"""
core.py — Public factory functions for minidblite.
"""

from .database import Database


def create_database(db_name: str = "database_session.db") -> Database:
    """
    Create (or open) a SQLite database and return a :class:`Database` object.

    This is the primary entry-point for minidblite. The database file is
    created on disk automatically if it does not already exist.
    Pass ``":memory:"`` to use a temporary in-memory database (useful for
    testing or scripts that don't need persistence).

    Args:
        db_name: Filename / path for the SQLite database.
                 Defaults to ``"database_session.db"`` in the current
                 working directory.

    Returns:
        A connected :class:`~minidblite.database.Database` instance.

    Example::

        import minidblite

        db = minidblite.create_database("my_app.db")

        db = minidblite.create_database(":memory:")

        with minidblite.create_database("my_app.db") as db:
            db.new_table("users")
    """
    return Database(db_name=db_name)