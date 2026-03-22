"""
utils.py — Utility helpers for minidblite.
"""

from typing import Any


TYPE_MAP: dict[type, str] = {
    int: "INTEGER",
    str: "TEXT",
    float: "REAL",
    bool: "INTEGER",
    bytes: "BLOB",
}


def python_type_to_sql(python_type: type) -> str:
    """
    Convert a Python type to its SQLite column type string.

    Args:
        python_type: A Python type (int, str, float, etc.)

    Returns:
        SQLite type string (e.g. "TEXT", "INTEGER")

    Raises:
        TypeError: If the type is not supported.
    """
    sql_type = TYPE_MAP.get(python_type)
    if sql_type is None:
        supported = ", ".join(t.__name__ for t in TYPE_MAP)
        raise TypeError(
            f"Unsupported type '{python_type.__name__}'. "
            f"Supported types: {supported}"
        )
    return sql_type


def build_success(message: str, data: Any = None) -> dict:
    """Build a structured success response."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def build_error(message: str, error: Exception | None = None) -> dict:
    """Build a structured error response."""
    return {
        "success": False,
        "message": message,
        "error": str(error) if error else None,
        "data": None,
    }


def validate_identifier(name: str) -> bool:
    """
    Validate that a table or column name is safe to use in SQL.
    Allows only alphanumerics and underscores.

    Args:
        name: The identifier to validate.

    Returns:
        True if valid, False otherwise.
    """
    import re
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name))