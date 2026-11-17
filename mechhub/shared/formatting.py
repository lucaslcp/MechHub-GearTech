"""Formatação de números e datas no padrão brasileiro (filtros Jinja)."""
import math
from datetime import datetime, timezone


def fmt_num(value, decimals: int = 2, empty: str = "—") -> str:
    """1234.5 → '1.234,50'."""
    if value is None:
        return empty
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return empty
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return fmt_num(value * 100, decimals) + " %"


def fmt_dt(value: datetime | None) -> str:
    """O banco guarda horários em UTC; a tela mostra no fuso do computador."""
    if not value:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%d/%m/%Y %H:%M")


def register_filters(app):
    app.add_template_filter(fmt_num, "num")
    app.add_template_filter(fmt_pct, "pct")
    app.add_template_filter(fmt_dt, "dt")
