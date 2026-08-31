import pytest
from fener import models  # noqa: F401
from fener.db import Base, make_engine
from sqlalchemy.orm import Session


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
