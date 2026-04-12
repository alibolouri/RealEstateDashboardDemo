from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.integration_catalog import IntegrationCatalog
from app.models.integration_config import IntegrationConfig


SECRET_FIELD_TYPES = {"password", "secret"}


def get_catalog_entries(db: Session) -> list[IntegrationCatalog]:
    statement = (
        select(IntegrationCatalog)
        .options(joinedload(IntegrationCatalog.config))
        .order_by(IntegrationCatalog.category.asc(), IntegrationCatalog.sort_order.asc())
    )
    return list(db.scalars(statement).unique().all())


def get_grouped_catalog_entries(db: Session) -> list[tuple[str, list[IntegrationCatalog]]]:
    groups: dict[str, list[IntegrationCatalog]] = defaultdict(list)
    for catalog in get_catalog_entries(db):
        groups[catalog.category].append(catalog)
    return sorted(groups.items(), key=lambda item: item[0])


def get_catalog_entry(db: Session, catalog_id: int) -> IntegrationCatalog | None:
    statement = (
        select(IntegrationCatalog)
        .options(joinedload(IntegrationCatalog.config))
        .where(IntegrationCatalog.id == catalog_id)
    )
    return db.scalar(statement)


def get_or_create_integration_config(db: Session, catalog_id: int) -> IntegrationConfig:
    config = db.scalar(select(IntegrationConfig).where(IntegrationConfig.catalog_id == catalog_id))
    if config is not None:
        return config

    config = IntegrationConfig(
        catalog_id=catalog_id,
        enabled=False,
        connection_status="not_configured",
        settings_data={},
        notes=None,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def has_secret_value(config: IntegrationConfig | None, field_name: str) -> bool:
    if config is None:
        return False
    return bool(config.settings_data.get(field_name))


def get_non_secret_field_value(config: IntegrationConfig | None, field_name: str) -> str:
    if config is None:
        return ""
    value = config.settings_data.get(field_name, "")
    return "" if isinstance(value, bool) else str(value)


def save_integration_config(
    db: Session,
    *,
    catalog: IntegrationCatalog,
    form_data: dict[str, str],
) -> IntegrationConfig:
    config = get_or_create_integration_config(db, catalog.id)
    settings_data = dict(config.settings_data or {})

    enabled = form_data.get("enabled") == "on"
    notes = form_data.get("notes", "").strip() or None

    for field in catalog.config_fields:
        name = field["name"]
        field_type = field.get("type", "text")
        if field_type == "checkbox":
            settings_data[name] = form_data.get(name) == "on"
            continue

        raw_value = form_data.get(name, "")
        if field_type in SECRET_FIELD_TYPES:
            if raw_value.strip():
                settings_data[name] = raw_value.strip()
            continue

        settings_data[name] = raw_value.strip()

    has_any_saved_value = any(bool(value) for value in settings_data.values())
    if enabled and has_any_saved_value:
        connection_status = "configured"
    elif enabled:
        connection_status = "needs_attention"
    elif has_any_saved_value:
        connection_status = "saved_disabled"
    else:
        connection_status = "not_configured"

    config.enabled = enabled
    config.connection_status = connection_status
    config.settings_data = settings_data
    config.notes = notes
    db.add(config)
    db.commit()
    db.refresh(config)
    return config
