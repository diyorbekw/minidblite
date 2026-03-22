"""
minidblite — A lightweight, beginner-friendly SQLite wrapper.

Quick start::

    import minidblite

    db = minidblite.create_database("my_app.db")

    db.new_table("users")
    db.new_column("name", str)
    db.new_column("age", int)

    db.add("users", name="Ali", age=20)
    db.add("users", name="Sara", age=25)

    result = db.get("users")
    result.decorate()          # pretty-print to terminal

    db.update("users", row_id=1, name="Vali")
    db.delete("users", name="Vali")
"""

import logging

from .core import create_database
from .database import Database
from .formatter import QueryResult

__all__ = [
    "create_database",
    "Database",
    "QueryResult",
]

__version__ = "0.1.1"
__author__ = "minidblite contributors"

# Configure a default null handler so library users don't see
# "No handlers could be found" warnings if they haven't set up logging.
logging.getLogger("minidblite").addHandler(logging.NullHandler())