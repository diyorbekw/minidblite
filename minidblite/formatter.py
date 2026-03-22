"""
formatter.py — Result wrapper with decorated terminal output for minidblite.
"""

from __future__ import annotations

from typing import Any


class QueryResult:
    """
    Wraps raw SQLite rows and their column names.

    Provides dict-like access and a `.decorate()` method for
    pretty terminal output via tabulate (or a built-in fallback).
    """

    def __init__(self, rows: list[tuple], columns: list[str]) -> None:
        self._rows = rows
        self._columns = columns

    @property
    def rows(self) -> list[tuple]:
        """Raw tuple rows as returned by sqlite3."""
        return self._rows

    @property
    def columns(self) -> list[str]:
        """Column names for this result set."""
        return self._columns

    @property
    def records(self) -> list[dict[str, Any]]:
        """Each row as a dictionary keyed by column name."""
        return [dict(zip(self._columns, row)) for row in self._rows]

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.records[index]

    def __bool__(self) -> bool:
        return bool(self._rows)

    def __repr__(self) -> str:
        return f"QueryResult(rows={len(self._rows)}, columns={self._columns})"

    def decorate(self, tablefmt: str = "rounded_outline") -> str:
        """
        Return a beautifully formatted table string and print it.

        Uses *tabulate* when available; falls back to a simple
        built-in ASCII renderer so the library works without it.

        Args:
            tablefmt: Any tabulate table format string.
                      Defaults to ``"rounded_outline"`` for a modern look.

        Returns:
            The formatted table as a string (also printed to stdout).
        """
        if not self._rows:
            msg = "  (no rows returned)"
            print(msg)
            return msg

        try:
            from tabulate import tabulate
            table = tabulate(
                self._rows,
                headers=self._columns,
                tablefmt=tablefmt,
                numalign="right",
                stralign="left",
            )
        except ImportError:
            table = self._fallback_table()

        print(table)
        return table

    def _fallback_table(self) -> str:
        """Minimal built-in table renderer used when tabulate is absent."""
        col_widths = [len(c) for c in self._columns]
        for row in self._rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
        header = "| " + " | ".join(
            c.ljust(col_widths[i]) for i, c in enumerate(self._columns)
        ) + " |"

        lines = [sep, header, sep]
        for row in self._rows:
            line = "| " + " | ".join(
                str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
            ) + " |"
            lines.append(line)
        lines.append(sep)
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize the result set to a JSON string.

        Args:
            indent: JSON indentation level (default 2).

        Returns:
            A JSON-encoded string of all records.
        """
        import json
        return json.dumps(self.records, indent=indent, default=str)

    def to_csv(self) -> str:
        """
        Serialize the result set to a CSV string.

        Returns:
            A CSV-formatted string including a header row.
        """
        import csv
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self._columns)
        writer.writeheader()
        writer.writerows(self.records)
        return buf.getvalue()