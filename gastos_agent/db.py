"""Acceso a la base de datos SQLite donde se guardan los gastos."""
import os
import sqlite3
from pathlib import Path

DB_POR_DEFECTO = Path(__file__).resolve().parent.parent / "gastos.db"


def get_connection() -> sqlite3.Connection:
    """Abre la conexión (la ruta se puede cambiar con la variable GASTOS_DB) y crea la tabla si no existe."""
    ruta = os.environ.get("GASTOS_DB", str(DB_POR_DEFECTO))
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto REAL NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
        """
    )
    return conn
