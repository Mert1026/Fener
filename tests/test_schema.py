from decimal import Decimal

import pytest
from fener.models import Deployment, Model, Provider
from sqlalchemy.exc import IntegrityError


def test_deployment_preserves_access_and_upstream(session):
    session.add_all(
        [
            Provider(id="market", name="Market"),
            Provider(id="upstream", name="Upstream"),
            Model(id="m", identity_key="publisher/m", name="Model"),
        ]
    )
    session.flush()
    session.add(
        Deployment(
            id="d",
            model_id="m",
            access_provider_id="market",
            upstream_provider_id="upstream",
            api_model_id="m",
            variant="upstream",
        )
    )
    session.commit()
    deployment = session.get(Deployment, "d")
    assert deployment.access_provider_id == "market"
    assert deployment.upstream_provider_id == "upstream"


def test_identity_is_unique(session):
    session.add_all(
        [Model(id="a", identity_key="same", name="A"), Model(id="b", identity_key="same", name="B")]
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_are_enforced(session):
    session.add(
        Deployment(id="d", model_id="missing", access_provider_id="missing", api_model_id="x")
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_money_normalization_is_decimal():
    from fener.sources.contracts import NativePrice

    price = NativePrice(metric="input_tokens", amount="0.000000123456", quantity=1)
    assert price.normalized == Decimal("0.123456")
