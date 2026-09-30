"""Nombres vigentes y equivalencias para registros históricos."""
import re


def canonical_catalog_value(field, value):
    if not isinstance(value, str):
        return value
    key = re.sub(r"[\s_-]+", " ", value.strip()).casefold()
    if field == "Segmento" and key in {"sales support", "free market", "b2b"}:
        return "B2B"
    if field in {"Producto", "Segmento", "Aliado"} and key in {"lighting", "lightning", "navidad"}:
        return "Navidad"
    return value
