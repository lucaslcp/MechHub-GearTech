"""Serviço compartilhado de Histórico."""
from ..extensions import db
from .models import HistoryEntry


def log_event(organization_id: int, user_id: int | None, module: str, action: str, description: str) -> HistoryEntry:
    entry = HistoryEntry(
        organization_id=organization_id,
        user_id=user_id,
        module=module,
        action=action,
        description=description[:300],
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def recent_events(organization_id: int, module: str | None = None, limit: int = 20) -> list[HistoryEntry]:
    query = HistoryEntry.query.filter_by(organization_id=organization_id)
    if module:
        query = query.filter_by(module=module)
    return query.order_by(HistoryEntry.created_at.desc(), HistoryEntry.id.desc()).limit(limit).all()
