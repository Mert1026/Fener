import importlib.util
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def test_setup_generates_matching_unique_credentials_and_explicit_sqlite():
    spec = importlib.util.spec_from_file_location("fener_manage", Path("scripts/manage.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    template = Path(".env.example").read_text(encoding="utf-8")
    first = dotenv_values(stream=StringIO(module.local_environment(template, False)))
    second = dotenv_values(stream=StringIO(module.local_environment(template, False)))
    assert make_url(first["DATABASE_URL"]).password == first["POSTGRES_PASSWORD"]
    assert len(first["POSTGRES_PASSWORD"]) == 64
    assert first["POSTGRES_PASSWORD"] != second["POSTGRES_PASSWORD"]
    assert first["FENER_ADMIN_KEY"] != second["FENER_ADMIN_KEY"]
    sqlite = dotenv_values(stream=StringIO(module.local_environment(template, True)))
    assert sqlite["DATABASE_URL"] == "sqlite:///.data/fener.db"
