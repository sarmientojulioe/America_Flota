"""Helpers para importación masiva por Excel/CSV."""
import io
import pandas as pd

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def leer_archivo(uploaded) -> pd.DataFrame:
    """Lee un archivo subido (.xlsx o .csv) a DataFrame de strings, con
    encabezados normalizados a minúscula y sin NaN (celdas vacías = '')."""
    nombre = uploaded.name.lower()
    if nombre.endswith(".csv"):
        df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(uploaded, dtype=str).fillna("")
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def plantilla_excel(columnas: list[str], ejemplo: dict) -> bytes:
    """Genera un .xlsx con los encabezados y una fila de ejemplo."""
    df = pd.DataFrame([ejemplo], columns=columnas)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name="Plantilla")
    return buf.getvalue()


def parse_bool(valor) -> bool:
    """Interpreta sí/no, true/false, 1/0, x, ✓ como booleano."""
    return str(valor).strip().lower() in ("1", "true", "verdadero", "si", "sí", "x", "✓", "yes")
