from app.db import sqlalchemy_url


def test_both_postgres_spellings_use_the_psycopg_driver() -> None:
    # Hosts such as Railway hand out the short `postgres://` form.
    assert sqlalchemy_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert sqlalchemy_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"


def test_a_url_that_already_names_a_driver_is_left_alone() -> None:
    assert sqlalchemy_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
