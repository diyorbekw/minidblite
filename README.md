# minidblite 🗃️

> A lightweight, beginner-friendly SQLite wrapper for Python — no SQL required.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://claude.ai/chat/LICENSE)

---

## What is minidblite?

`minidblite` lets you create and work with a local SQLite database using
clean, Pythonic method calls. No SQL knowledge needed.

```python
import minidblite

db = minidblite.create_database("my_app.db")

db.new_table("users")
db.new_column("name", str)
db.new_column("age", int)

db.add("users", name="Ali", age=20)

db.get("users").decorate()   # pretty-print to terminal
```

---

## Installation

```bash
pip install minidblite
```

> Requires Python 3.10+ and installs `tabulate` automatically.

---

## Quick Start

```python
import minidblite

# 1. Create (or open) a database
db = minidblite.create_database("shop.db")

# 2. Define a table
db.new_table("products")
db.new_column("name",  str)
db.new_column("price", float)
db.new_column("stock", int)

# 3. Insert rows
db.add("products", name="Widget",  price=9.99,  stock=100)
db.add("products", name="Gadget",  price=24.99, stock=50)
db.add("products", name="Doohickey", price=4.49, stock=200)

# 4. Display all rows
db.get("products").decorate()

# 5. Filter rows
cheap = db.get("products", name="Widget")
print(cheap.records)   # [{'id': 1, 'name': 'Widget', ...}]

# 6. Update a row
db.update("products", row_id=1, price=8.99)

# 7. Delete a row
db.delete("products", name="Doohickey")

# 8. Export to JSON
db.export_json("products", path="products.json")
```

---

## Context Manager

The database connection is closed automatically when used as a context manager:

```python
with minidblite.create_database("temp.db") as db:
    db.new_table("sessions")
    db.new_column("token", str)
    db.add("sessions", token="abc123")
# connection closed here
```

---

## API Reference

### `minidblite.create_database(db_name="database_session.db") → Database`

Create or open a SQLite database.

| Parameter   | Type    | Default                   | Description                                              |
| ----------- | ------- | ------------------------- | -------------------------------------------------------- |
| `db_name` | `str` | `"database_session.db"` | Filename or path. Use `":memory:"`for an in-memory DB. |

---

### `Database.new_table(table_name)`

Create a table (with an auto-increment `id` column).

```python
db.new_table("orders")
```

---

### `Database.new_column(column_name, data_type, table_name=None)`

Add a column to a table.

```python
db.new_column("email", str)           # uses last created table
db.new_column("score", float, table_name="players")
```

**Supported Python types:**

| Python    | SQLite  |
| --------- | ------- |
| `str`   | TEXT    |
| `int`   | INTEGER |
| `float` | REAL    |
| `bool`  | INTEGER |
| `bytes` | BLOB    |

---

### `Database.add(table_name, **columns) → dict`

Insert a row.

```python
db.add("users", name="Ali", age=20)
# → {'success': True, 'message': '...', 'data': {'id': 1}}
```

---

### `Database.get(table_name, **filters) → QueryResult`

Fetch rows, optionally filtered.

```python
all_users = db.get("users")
ali       = db.get("users", name="Ali")
```

#### `QueryResult` methods

| Method / Property                         | Description                                  |
| ----------------------------------------- | -------------------------------------------- |
| `.decorate(tablefmt="rounded_outline")` | Pretty-print to terminal; returns the string |
| `.records`                              | `list[dict]`— rows as dicts               |
| `.rows`                                 | `list[tuple]`— raw tuples                 |
| `.columns`                              | `list[str]`— column names                 |
| `.to_json(indent=2)`                    | Serialize to JSON string                     |
| `.to_csv()`                             | Serialize to CSV string                      |
| `len(result)`                           | Number of rows                               |
| `result[0]`                             | First row as dict                            |
| `for row in result`                     | Iterate over dicts                           |

---

### `Database.update(table_name, row_id, **new_values) → dict`

Update a row by its `id`.

```python
db.update("users", row_id=1, name="Vali", age=21)
```

---

### `Database.delete(table_name, is_all=False, **filters) → dict`

Delete rows.

```python
db.delete("users", name="Vali")             # first match only
db.delete("users", is_all=True, age=20)     # all matches
db.delete("users", is_all=True)             # ALL rows in table
```

---

### `Database.schema(table_name) → dict`

Return column metadata.

```python
info = db.schema("users")
# info['data']['columns'] → [{'name': 'id', 'type': 'INTEGER', ...}, ...]
```

---

### `Database.export_json(table_name, path=None) → dict`

Export table data to JSON.

```python
db.export_json("users", path="users.json")   # write file
json_str = db.export_json("users")["data"]   # get string
```

---

### `Database.list_tables() → list[str]`

Return all table names in the database.

---

### `Database.drop_table(table_name) → dict`

Drop a table permanently.

---

### `Database.close() → dict`

Close the connection. Called automatically by the context manager.

---

## Structured Responses

Every write method (`add`, `update`, `delete`, `new_table`, `new_column`, …)
returns a dict:

```python
# Success
{'success': True,  'message': 'Row inserted ...', 'data': {'id': 3}}

# Failure (no crash)
{'success': False, 'message': 'Table "ghost" does not exist.', 'error': '...', 'data': None}
```

---

## Logging

Enable Python's built-in logging to see what minidblite is doing:

```python
import logging
logging.basicConfig(level=logging.INFO)

import minidblite
db = minidblite.create_database()
db.new_table("logs")   # INFO:minidblite:Table 'logs' created ...
```

---

## Running Tests

```bash
pip install minidblite[dev]
pytest tests/ -v
```

---

## Project Structure

```
minidblite/
├── minidblite/
│   ├── __init__.py     ← public API
│   ├── core.py         ← create_database() factory
│   ├── database.py     ← Database class
│   ├── formatter.py    ← QueryResult & pretty-print
│   └── utils.py        ← type mapping, validators, response builders
├── tests/
│   └── test_basic.py
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

---

## License

MIT — see [LICENSE](https://claude.ai/chat/LICENSE).
# minidblite
