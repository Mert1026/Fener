"""Data maintenance for historical ingestion artifacts.

Some sources publish a model under several keys (LiteLLM ships both bare
legacy keys and namespaced keys). Before the concurrent-observation guard,
every key resolved to the same deployment and overwrote the previous write
within one sync, leaving half-writes in the fact chains: two facts for the
same entity/field recorded at the same instant with different values, paired
opposite-direction market events, and alternating price observations.
"""

import json
from collections import defaultdict
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection


def _canonical(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            pass
    return json.dumps(value, sort_keys=True, default=str)


def _moment(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def purge_concurrent_conflict_artifacts(connection: Connection) -> int:
    """Delete the losing half-writes of same-instant conflicting observations.

    Keeps the currently displayed fact of every chain plus all legitimately
    sequenced observations (one write per instant), and removes the market
    events, price rows, and conflicts that referenced the deleted halves.
    Returns the number of deleted facts. Raw snapshots stay untouched, so the
    full provenance of every removed observation remains auditable.
    """
    facts = connection.execute(
        text("SELECT id, entity_type, entity_id, field, value, observed_at FROM fact_observations")
    ).fetchall()

    groups: dict[tuple[str, str, str, str], list[tuple[str, str]]] = defaultdict(list)
    meta: dict[str, tuple[str, str, str, Any]] = {}
    for fact_id, entity_type, entity_id, field, value, observed_at in facts:
        moment = _moment(observed_at)
        groups[(entity_type, entity_id, field, moment)].append((fact_id, _canonical(value)))
        meta[fact_id] = (entity_type, entity_id, field, observed_at)

    conflicted: set[str] = set()
    for members in groups.values():
        if len({value for _, value in members}) > 1:
            conflicted.update(fact_id for fact_id, _ in members)
    if not conflicted:
        return 0

    # The displayed value always survives; conflicting half-writes do not.
    current = connection.execute(text("SELECT observation_id FROM current_facts")).fetchall()
    removed = conflicted - {row[0] for row in current}
    if not removed:
        return 0

    removed_meta = {fact_id: meta[fact_id] for fact_id in removed}

    # Cross-source conflict records that referenced the deleted halves.
    connection.execute(
        text(
            "DELETE FROM source_conflicts WHERE observation_a IN :ids OR observation_b IN :ids"
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": sorted(removed)},
    )
    connection.execute(
        text("DELETE FROM pricing_observations WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        ),
        {"ids": sorted(removed)},
    )

    # Market events announcing a deleted half-write: same entity, same field
    # title, same instant, and a new value equal to the deleted fact's value.
    events = connection.execute(
        text("SELECT id, entity_type, entity_id, title, detected_at, new_value FROM market_events")
    ).fetchall()
    event_index: dict[tuple[str, str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for event_id, entity_type, entity_id, title, detected_at, new_value in events:
        event_key = (entity_type, entity_id, title, _moment(detected_at))
        event_index[event_key].append((event_id, _canonical(new_value)))
    doomed_events: set[str] = set()
    for fact_id, (entity_type, entity_id, field, observed_at) in removed_meta.items():
        value = next(
            v
            for i, v in groups[(entity_type, entity_id, field, _moment(observed_at))]
            if i == fact_id
        )
        event_key = (
            entity_type,
            entity_id,
            f"{field.replace('_', ' ')} changed",
            _moment(observed_at),
        )
        for event_id, event_value in event_index.get(event_key, []):
            if event_value == value:
                doomed_events.add(event_id)
    if doomed_events:
        connection.execute(
            text("DELETE FROM market_events WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": sorted(doomed_events)},
        )

    # Claim and current pointers only ever reference the surviving tip; still,
    # repoint any straggler to the earliest surviving fact of its chain.
    survivors: dict[tuple[str, str, str], str] = {}
    for fact_id in set(meta) - removed:
        entity_type, entity_id, field, observed_at = meta[fact_id]
        key = (entity_type, entity_id, field)
        known = survivors.get(key)
        if known is None or observed_at < meta[known][3]:
            survivors[key] = fact_id
    for table in ("current_facts", "source_claims"):
        pointers = connection.execute(text(f"SELECT observation_id FROM {table}")).fetchall()
        dangling = sorted({row[0] for row in pointers if row[0] in removed})
        for observation_id in dangling:
            entity_type, entity_id, field, _ = meta[observation_id]
            survivor = survivors.get((entity_type, entity_id, field))
            if survivor:
                connection.execute(
                    text(
                        f"UPDATE {table} SET observation_id = :survivor"
                        " WHERE observation_id = :observation"
                    ),
                    {"survivor": survivor, "observation": observation_id},
                )

    connection.execute(
        text("DELETE FROM fact_observations WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        ),
        {"ids": sorted(removed)},
    )
    return len(removed)
