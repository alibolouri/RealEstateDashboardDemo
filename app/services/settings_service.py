from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.app_setting import AppSetting
from app.models.realtor import Realtor


env_settings = get_settings()


@dataclass
class RuntimeAppSettings:
    fixed_contact_number: str
    default_realtor_id: int
    chat_result_limit: int
    default_desired_city_fallback: str | None
    dashboard_density: str
    dashboard_table_page_size: int
    feature_integrations_panel: bool
    feature_lead_routing_writes: bool
    feature_catalog_visibility: bool


def get_or_create_app_settings(db: Session) -> AppSetting:
    app_settings = db.get(AppSetting, 1)
    if app_settings is not None:
        return app_settings

    default_realtor_id = env_settings.default_realtor_id
    if db.get(Realtor, default_realtor_id) is None:
        fallback_realtor = db.query(Realtor).order_by(Realtor.id.asc()).first()
        if fallback_realtor is not None:
            default_realtor_id = fallback_realtor.id

    app_settings = AppSetting(
        id=1,
        fixed_contact_number=env_settings.fixed_contact_number,
        default_realtor_id=default_realtor_id,
        chat_result_limit=5,
        default_desired_city_fallback=None,
        dashboard_density="comfortable",
        dashboard_table_page_size=10,
        feature_integrations_panel=True,
        feature_lead_routing_writes=True,
        feature_catalog_visibility=True,
    )
    db.add(app_settings)
    db.commit()
    db.refresh(app_settings)
    return app_settings


def get_runtime_settings(db: Session) -> RuntimeAppSettings:
    app_settings = get_or_create_app_settings(db)
    return RuntimeAppSettings(
        fixed_contact_number=app_settings.fixed_contact_number,
        default_realtor_id=app_settings.default_realtor_id,
        chat_result_limit=app_settings.chat_result_limit,
        default_desired_city_fallback=app_settings.default_desired_city_fallback,
        dashboard_density=app_settings.dashboard_density,
        dashboard_table_page_size=app_settings.dashboard_table_page_size,
        feature_integrations_panel=app_settings.feature_integrations_panel,
        feature_lead_routing_writes=app_settings.feature_lead_routing_writes,
        feature_catalog_visibility=app_settings.feature_catalog_visibility,
    )


def update_app_settings(
    db: Session,
    *,
    fixed_contact_number: str,
    default_realtor_id: int,
    chat_result_limit: int,
    default_desired_city_fallback: str | None,
    dashboard_density: str,
    dashboard_table_page_size: int,
    feature_integrations_panel: bool,
    feature_lead_routing_writes: bool,
    feature_catalog_visibility: bool,
) -> AppSetting:
    app_settings = get_or_create_app_settings(db)
    app_settings.fixed_contact_number = fixed_contact_number.strip()
    app_settings.default_realtor_id = default_realtor_id
    app_settings.chat_result_limit = chat_result_limit
    app_settings.default_desired_city_fallback = (
        default_desired_city_fallback.strip() if default_desired_city_fallback else None
    )
    app_settings.dashboard_density = dashboard_density
    app_settings.dashboard_table_page_size = dashboard_table_page_size
    app_settings.feature_integrations_panel = feature_integrations_panel
    app_settings.feature_lead_routing_writes = feature_lead_routing_writes
    app_settings.feature_catalog_visibility = feature_catalog_visibility
    db.add(app_settings)
    db.commit()
    db.refresh(app_settings)
    return app_settings


def ensure_lead_routing_enabled(db: Session) -> None:
    settings_snapshot = get_runtime_settings(db)
    if not settings_snapshot.feature_lead_routing_writes:
        raise PermissionError("Lead routing is disabled in dashboard settings")
