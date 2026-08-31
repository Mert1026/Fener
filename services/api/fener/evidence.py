"""Append-only observation writes with deterministic, fact-scoped precedence."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fener.models import (
    Conflict,
    CurrentFact,
    Deployment,
    Fact,
    MarketEvent,
    Model,
    SourceClaim,
    SourceRecord,
)


def digest(*values: Any) -> str:
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str, ensure_ascii=False).encode()
    ).hexdigest()


def json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


class EvidenceWriter:
    def __init__(self, session: Session, source_id: str, observed_at: datetime):
        self.session = session
        self.source_id = source_id
        self.observed_at = observed_at
        self.facts = {row.id: row for row in session.scalars(select(Fact))}
        self.claims = {
            (r.source_id, r.entity_type, r.entity_id, r.field): r
            for r in session.scalars(select(SourceClaim))
        }
        self.current = {
            (r.entity_type, r.entity_id, r.field): r for r in session.scalars(select(CurrentFact))
        }
        self.by_field: dict[tuple[str, str, str], dict[str, Fact]] = defaultdict(dict)
        for claim in self.claims.values():
            self.by_field[(claim.entity_type, claim.entity_id, claim.field)][claim.source_id] = (
                self.facts[claim.observation_id]
            )
        self.conflicts = {r.id for r in session.scalars(select(Conflict))}

    def observe(
        self,
        entity_type: str,
        entity_id: str,
        field: str,
        value: Any,
        record: SourceRecord,
        authority: int,
        verification: str,
    ) -> tuple[Fact, bool]:
        value = json_value(value)
        key = (entity_type, entity_id, field)
        source_key = (self.source_id, *key)
        previous_claim = self.claims.get(source_key)
        previous = self.facts[previous_claim.observation_id] if previous_claim else None
        if previous is not None and previous.value == value:
            return previous, False
        # Chain the previous observation so A -> B -> A remains three observations.
        fact = Fact(
            id=digest(source_key, record.id, value, previous.id if previous else None),
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            value=value,
            source_record_id=record.id,
            verification=verification,
            authority=authority,
            observed_at=self.observed_at,
        )
        self.session.add(fact)
        self.session.flush()
        self.facts[fact.id] = fact
        if previous_claim:
            previous_claim.observation_id = fact.id
        else:
            claim = SourceClaim(
                source_id=self.source_id,
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                observation_id=fact.id,
            )
            self.session.add(claim)
            self.claims[source_key] = claim
        other_claims = self.by_field[key]
        for other_source, other in other_claims.items():
            if other_source == self.source_id or other.value == value:
                continue
            conflict_id = digest("conflict", *sorted([other.id, fact.id]))
            if conflict_id not in self.conflicts:
                different_authority = other.authority != authority
                self.session.add(
                    Conflict(
                        id=conflict_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        field=field,
                        observation_a=other.id,
                        observation_b=fact.id,
                        status="automatically_resolved" if different_authority else "open",
                        resolution="Higher fact-scoped source authority"
                        if different_authority
                        else None,
                        resolved_at=self.observed_at if different_authority else None,
                    )
                )
                self.conflicts.add(conflict_id)
        other_claims[self.source_id] = fact
        # UTC ISO timestamps sort identically and work with both SQLite and PostgreSQL datetimes.
        winner = max(
            other_claims.values(), key=lambda r: (r.authority, r.observed_at.isoformat(), r.id)
        )
        entity_class = (
            Model if entity_type == "model" else Deployment if entity_type == "deployment" else None
        )
        projected = (
            {"name", "family", "context_window", "open_weights", "release_date"}
            if entity_type == "model"
            else {
                "context_window",
                "max_output",
                "tool_calling",
                "structured_output",
                "image_input",
                "reasoning",
                "availability",
            }
        )
        if entity_class and field in projected:
            entity = self.session.get(entity_class, entity_id)
            if entity is not None:
                setattr(entity, field, winner.value)
        current = self.current.get(key)
        old = self.facts[current.observation_id] if current else None
        if current:
            current.observation_id = winner.id
        else:
            current = CurrentFact(
                entity_type=entity_type, entity_id=entity_id, field=field, observation_id=winner.id
            )
            self.current[key] = current
            self.session.add(current)
        if old is not None and old.value != winner.value:
            importance = "low"
            event_type = "metadata_change"
            if field.startswith("price."):
                event_type = "price_change"
                before, after = Decimal(old.value["amount"]), Decimal(winner.value["amount"])
                if before > 0 and abs(after - before) / before >= Decimal("0.30"):
                    importance = "high"
            elif field == "context_window":
                event_type = "context_change"
            elif field == "availability":
                event_type = "availability_change"
            elif isinstance(value, bool):
                event_type = "capability_change"
            self.session.add(
                MarketEvent(
                    id=digest("change", old.id, winner.id),
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=f"{field.replace('_', ' ')} changed",
                    old_value=old.value,
                    new_value=winner.value,
                    source_record_id=winner.source_record_id,
                    importance=importance,
                    detected_at=self.observed_at,
                )
            )
        return fact, True
