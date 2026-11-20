"""Herramientas del agente de gastos.

Todas devuelven un diccionario con la clave "status" ("success" o "error").
Los docstrings son importantes: ADK se los muestra al modelo para que decida
cuándo y cómo usar cada herramienta.
"""
from datetime import date, datetime

from .db import get_connection


def _parsear_fecha(valor: str | None, nombre: str) -> tuple[str | None, str | None]:
    """Devuelve (fecha_iso, error). Si valor es None devuelve (None, None)."""
    if valor is None or str(valor).strip() == "":
        return None, None
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date().isoformat(), None
    except ValueError:
        return None, f"La fecha '{nombre}' no es válida: '{valor}'. Usá el formato AAAA-MM-DD."


def registrar_gasto(monto: float, categoria: str, descripcion: str, fecha: str | None = None) -> dict:
    """Registra un nuevo gasto en la base de datos.

    Args:
        monto: importe del gasto, número mayor a 0.
        categoria: categoría del gasto (ej. comida, transporte, salud, ocio).
        descripcion: breve detalle del gasto.
        fecha: fecha en formato AAAA-MM-DD. Si no se indica, se usa la de hoy.

    Returns:
        dict con status "success" y el gasto creado (incluye su id), o status "error" con el motivo.
    """
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        return {"status": "error", "mensaje": f"El monto debe ser un número, se recibió: {monto!r}."}
    if monto != monto or monto in (float("inf"), float("-inf")) or monto <= 0:
        return {"status": "error", "mensaje": "El monto debe ser un número mayor a 0."}

    categoria = (categoria or "").strip().lower()
    if not categoria:
        return {"status": "error", "mensaje": "La categoría no puede estar vacía."}
    descripcion = (descripcion or "").strip() or "sin descripción"

    fecha_iso, error = _parsear_fecha(fecha, "fecha")
    if error:
        return {"status": "error", "mensaje": error}
    fecha_iso = fecha_iso or date.today().isoformat()
    if fecha_iso > date.today().isoformat():
        return {"status": "error", "mensaje": "La fecha del gasto no puede ser futura."}

    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO gastos (monto, categoria, descripcion, fecha) VALUES (?, ?, ?, ?)",
            (monto, categoria, descripcion, fecha_iso),
        )
        nuevo_id = cur.lastrowid
    return {
        "status": "success",
        "mensaje": "Gasto registrado correctamente.",
        "gasto": {"id": nuevo_id, "monto": monto, "categoria": categoria,
                  "descripcion": descripcion, "fecha": fecha_iso},
    }


def listar_gastos(categoria: str | None = None, desde: str | None = None,
                  hasta: str | None = None, limite: int = 20) -> dict:
    """Lista gastos registrados, del más reciente al más antiguo, con filtros opcionales.

    Args:
        categoria: filtrar por categoría (opcional).
        desde: fecha mínima AAAA-MM-DD, inclusive (opcional).
        hasta: fecha máxima AAAA-MM-DD, inclusive (opcional).
        limite: cantidad máxima de gastos a devolver (1 a 100, por defecto 20).

    Returns:
        dict con status "success", la lista "gastos" (puede estar vacía) y un mensaje, o status "error".
    """
    desde_iso, error = _parsear_fecha(desde, "desde")
    if error:
        return {"status": "error", "mensaje": error}
    hasta_iso, error = _parsear_fecha(hasta, "hasta")
    if error:
        return {"status": "error", "mensaje": error}
    if desde_iso and hasta_iso and desde_iso > hasta_iso:
        return {"status": "error", "mensaje": "'desde' no puede ser posterior a 'hasta'."}
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        return {"status": "error", "mensaje": "El límite debe ser un número entero."}
    if not 1 <= limite <= 100:
        return {"status": "error", "mensaje": "El límite debe estar entre 1 y 100."}

    sql, params = "SELECT * FROM gastos WHERE 1=1", []
    if categoria and categoria.strip():
        sql += " AND categoria = ?"
        params.append(categoria.strip().lower())
    if desde_iso:
        sql += " AND fecha >= ?"
        params.append(desde_iso)
    if hasta_iso:
        sql += " AND fecha <= ?"
        params.append(hasta_iso)
    sql += " ORDER BY fecha DESC, id DESC LIMIT ?"
    params.append(limite)

    with get_connection() as conn:
        gastos = [dict(fila) for fila in conn.execute(sql, params)]
    if not gastos:
        return {"status": "success", "gastos": [], "mensaje": "No hay gastos que coincidan con esos filtros."}
    return {"status": "success", "gastos": gastos, "mensaje": f"Se encontraron {len(gastos)} gasto(s)."}


def resumen_gastos(desde: str | None = None, hasta: str | None = None) -> dict:
    """Calcula el total gastado y el desglose por categoría en un período.

    Args:
        desde: fecha mínima AAAA-MM-DD, inclusive (opcional).
        hasta: fecha máxima AAAA-MM-DD, inclusive (opcional).

    Returns:
        dict con status "success", total, cantidad, por_categoria y categoria_mayor_gasto,
        o status "error" si las fechas son inválidas. Sin datos devuelve total 0 y un mensaje.
    """
    desde_iso, error = _parsear_fecha(desde, "desde")
    if error:
        return {"status": "error", "mensaje": error}
    hasta_iso, error = _parsear_fecha(hasta, "hasta")
    if error:
        return {"status": "error", "mensaje": error}
    if desde_iso and hasta_iso and desde_iso > hasta_iso:
        return {"status": "error", "mensaje": "'desde' no puede ser posterior a 'hasta'."}

    sql, params = "SELECT categoria, SUM(monto) AS total, COUNT(*) AS cantidad FROM gastos WHERE 1=1", []
    if desde_iso:
        sql += " AND fecha >= ?"
        params.append(desde_iso)
    if hasta_iso:
        sql += " AND fecha <= ?"
        params.append(hasta_iso)
    sql += " GROUP BY categoria ORDER BY total DESC"

    with get_connection() as conn:
        filas = conn.execute(sql, params).fetchall()
    if not filas:
        return {"status": "success", "total": 0, "cantidad": 0, "por_categoria": {},
                "categoria_mayor_gasto": None, "mensaje": "No hay gastos en el período indicado."}
    por_categoria = {f["categoria"]: round(f["total"], 2) for f in filas}
    return {
        "status": "success",
        "total": round(sum(por_categoria.values()), 2),
        "cantidad": sum(f["cantidad"] for f in filas),
        "por_categoria": por_categoria,
        "categoria_mayor_gasto": filas[0]["categoria"],
        "mensaje": "Resumen calculado correctamente.",
    }


def eliminar_gasto(id_gasto: int) -> dict:
    """Elimina un gasto por su id. Confirmá con el usuario antes de usarla.

    Args:
        id_gasto: id numérico del gasto (se obtiene con listar_gastos).

    Returns:
        dict con status "success" y el gasto eliminado, o status "error" si el id es inválido o no existe.
    """
    try:
        id_num = int(id_gasto)
        if id_num != float(id_gasto):
            raise ValueError
    except (TypeError, ValueError):
        return {"status": "error", "mensaje": f"El id debe ser un número entero, se recibió: {id_gasto!r}."}
    if id_num <= 0:
        return {"status": "error", "mensaje": "El id debe ser un entero positivo."}

    with get_connection() as conn:
        fila = conn.execute("SELECT * FROM gastos WHERE id = ?", (id_num,)).fetchone()
        if fila is None:
            return {"status": "error", "mensaje": f"No existe un gasto con id {id_num}."}
        conn.execute("DELETE FROM gastos WHERE id = ?", (id_num,))
    return {"status": "success", "mensaje": f"Gasto {id_num} eliminado.", "gasto_eliminado": dict(fila)}
