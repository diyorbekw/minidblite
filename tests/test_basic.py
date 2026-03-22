"""
tests/test_basic.py — Unit tests for minidblite.

Run with:
    pytest tests/test_basic.py -v
"""

import pytest
import minidblite
from minidblite import create_database
from minidblite.formatter import QueryResult


# ---------------------------------------------------------------------------
# Fixture: fresh in-memory database for each test
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """Return a fresh in-memory Database instance."""
    database = create_database(":memory:")
    yield database
    database.close()


@pytest.fixture
def users_db(db):
    """Database with a 'users' table that has name (str) and age (int) columns."""
    db.new_table("users")
    db.new_column("name", str)
    db.new_column("age", int)
    return db


# ---------------------------------------------------------------------------
# create_database
# ---------------------------------------------------------------------------

class TestCreateDatabase:
    def test_returns_database_instance(self):
        db = create_database(":memory:")
        assert isinstance(db, minidblite.Database)
        db.close()

    def test_context_manager(self):
        with create_database(":memory:") as db:
            assert isinstance(db, minidblite.Database)

    def test_default_name(self):
        db = create_database(":memory:")
        assert db.db_name == ":memory:"
        db.close()


# ---------------------------------------------------------------------------
# new_table
# ---------------------------------------------------------------------------

class TestNewTable:
    def test_creates_table(self, db):
        result = db.new_table("products")
        assert result["success"] is True
        assert "products" in db.list_tables()

    def test_idempotent(self, db):
        db.new_table("items")
        result = db.new_table("items")   # should not raise
        assert result["success"] is True

    def test_invalid_name_rejected(self, db):
        result = db.new_table("123bad name!")
        assert result["success"] is False

    def test_sets_last_table_context(self, db):
        db.new_table("ctx_table")
        assert db._last_table == "ctx_table"


# ---------------------------------------------------------------------------
# new_column
# ---------------------------------------------------------------------------

class TestNewColumn:
    def test_adds_str_column(self, db):
        db.new_table("items")
        result = db.new_column("title", str)
        assert result["success"] is True
        assert "title" in db._get_columns("items")

    def test_adds_int_column(self, db):
        db.new_table("items")
        result = db.new_column("qty", int)
        assert result["success"] is True

    def test_adds_float_column(self, db):
        db.new_table("items")
        result = db.new_column("price", float)
        assert result["success"] is True

    def test_uses_last_table_context(self, db):
        db.new_table("auto_ctx")
        result = db.new_column("value", str)  # no table_name arg
        assert result["success"] is True

    def test_explicit_table_name(self, db):
        db.new_table("t1")
        db.new_table("t2")
        result = db.new_column("col_a", str, table_name="t1")
        assert result["success"] is True
        assert "col_a" in db._get_columns("t1")
        assert "col_a" not in db._get_columns("t2")

    def test_duplicate_column_is_noop(self, db):
        db.new_table("dup")
        db.new_column("email", str)
        result = db.new_column("email", str)   # duplicate
        assert result["success"] is True       # graceful skip

    def test_unsupported_type_fails(self, db):
        db.new_table("bad_types")
        result = db.new_column("data", list)   # list is not supported
        assert result["success"] is False

    def test_no_context_fails(self, db):
        result = db.new_column("orphan", str)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# add / insert
# ---------------------------------------------------------------------------

class TestAdd:
    def test_basic_insert(self, users_db):
        result = users_db.add("users", name="Ali", age=20)
        assert result["success"] is True
        assert result["data"]["id"] == 1

    def test_multiple_inserts(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Sara", age=25)
        rows = users_db.get("users")
        assert len(rows) == 2

    def test_insert_nonexistent_table_fails(self, db):
        result = db.add("ghost", name="nobody")
        assert result["success"] is False

    def test_insert_no_columns_fails(self, users_db):
        result = users_db.add("users")
        assert result["success"] is False

    def test_auto_increment_id(self, users_db):
        r1 = users_db.add("users", name="A", age=1)
        r2 = users_db.add("users", name="B", age=2)
        assert r2["data"]["id"] == r1["data"]["id"] + 1


# ---------------------------------------------------------------------------
# get / query
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_all(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Sara", age=25)
        result = users_db.get("users")
        assert isinstance(result, QueryResult)
        assert len(result) == 2

    def test_get_with_filter(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Sara", age=25)
        result = users_db.get("users", name="Ali")
        assert len(result) == 1
        assert result[0]["name"] == "Ali"

    def test_get_empty_table(self, users_db):
        result = users_db.get("users")
        assert len(result) == 0

    def test_get_nonexistent_table_returns_empty(self, db):
        result = db.get("ghost_table")
        assert isinstance(result, QueryResult)
        assert len(result) == 0

    def test_records_property(self, users_db):
        users_db.add("users", name="Ali", age=20)
        records = users_db.get("users").records
        assert isinstance(records, list)
        assert records[0]["name"] == "Ali"

    def test_iteration(self, users_db):
        users_db.add("users", name="X", age=1)
        for row in users_db.get("users"):
            assert "name" in row

    def test_decorate_returns_string(self, users_db):
        users_db.add("users", name="Ali", age=20)
        output = users_db.get("users").decorate()
        assert isinstance(output, str)
        assert "Ali" in output

    def test_to_json(self, users_db):
        import json
        users_db.add("users", name="Ali", age=20)
        json_str = users_db.get("users").to_json()
        data = json.loads(json_str)
        assert data[0]["name"] == "Ali"

    def test_to_csv(self, users_db):
        users_db.add("users", name="Ali", age=20)
        csv_str = users_db.get("users").to_csv()
        assert "name" in csv_str
        assert "Ali" in csv_str


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_single_field(self, users_db):
        users_db.add("users", name="Ali", age=20)
        result = users_db.update("users", row_id=1, name="Vali")
        assert result["success"] is True
        row = users_db.get("users", name="Vali")
        assert len(row) == 1

    def test_update_multiple_fields(self, users_db):
        users_db.add("users", name="Ali", age=20)
        result = users_db.update("users", row_id=1, name="Bob", age=99)
        assert result["success"] is True
        row = users_db.get("users")[0]
        assert row["name"] == "Bob"
        assert row["age"] == 99

    def test_update_nonexistent_id_fails(self, users_db):
        result = users_db.update("users", row_id=999, name="Ghost")
        assert result["success"] is False

    def test_update_no_values_fails(self, users_db):
        users_db.add("users", name="Ali", age=20)
        result = users_db.update("users", row_id=1)
        assert result["success"] is False

    def test_update_nonexistent_table_fails(self, db):
        result = db.update("ghost", row_id=1, name="X")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_first_match(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Ali", age=21)
        result = users_db.delete("users", name="Ali")
        assert result["success"] is True
        # One Ali should remain
        remaining = users_db.get("users", name="Ali")
        assert len(remaining) == 1

    def test_delete_all_matches(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Ali", age=21)
        result = users_db.delete("users", is_all=True, name="Ali")
        assert result["success"] is True
        assert len(users_db.get("users", name="Ali")) == 0

    def test_delete_all_rows(self, users_db):
        users_db.add("users", name="Ali", age=20)
        users_db.add("users", name="Sara", age=25)
        result = users_db.delete("users", is_all=True)
        assert result["success"] is True
        assert len(users_db.get("users")) == 0

    def test_delete_no_filter_no_all_warns(self, users_db):
        result = users_db.delete("users")
        assert result["success"] is False

    def test_delete_nonexistent_table_fails(self, db):
        result = db.delete("ghost", name="x")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# schema / extras
# ---------------------------------------------------------------------------

class TestSchema:
    def test_schema_returns_column_info(self, users_db):
        result = users_db.schema("users")
        assert result["success"] is True
        col_names = [c["name"] for c in result["data"]["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert "age" in col_names

    def test_schema_nonexistent_table_fails(self, db):
        result = db.schema("ghost")
        assert result["success"] is False


class TestExportJson:
    def test_export_json_no_path(self, users_db):
        users_db.add("users", name="Ali", age=20)
        result = users_db.export_json("users")
        assert result["success"] is True

    def test_export_json_to_file(self, users_db, tmp_path):
        users_db.add("users", name="Ali", age=20)
        out = tmp_path / "out.json"
        result = users_db.export_json("users", path=str(out))
        assert result["success"] is True
        assert out.exists()