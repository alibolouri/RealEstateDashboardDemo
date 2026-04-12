import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.integration_catalog import IntegrationCatalog
from app.models.integration_config import IntegrationConfig
from app.models.property import Property
from app.models.realtor import Realtor
from app.services.settings_service import get_or_create_app_settings


SEED_DIR = Path(__file__).resolve().parents[2] / "seed"


def _load_json(filename: str) -> list[dict]:
    file_path = SEED_DIR / filename
    with file_path.open("r", encoding="utf-8") as seed_file:
        return json.load(seed_file)


def seed_database(db: Session) -> None:
    has_realtors = db.scalar(select(Realtor.id).limit(1)) is not None
    has_properties = db.scalar(select(Property.id).limit(1)) is not None
    has_catalog_entries = db.scalar(select(IntegrationCatalog.id).limit(1)) is not None
    has_app_settings = db.scalar(select(AppSetting.id).limit(1)) is not None

    if not has_realtors:
        realtor_records = [Realtor(**payload) for payload in _load_json("realtors.json")]
        db.add_all(realtor_records)
        db.flush()

    if not has_properties:
        property_records = [Property(**payload) for payload in _load_json("properties.json")]
        db.add_all(property_records)

    db.commit()

    if not has_app_settings:
        get_or_create_app_settings(db)

    if not has_catalog_entries:
        catalog_records = [IntegrationCatalog(**payload) for payload in _load_json("integrations.json")]
        db.add_all(catalog_records)
        db.commit()

    catalog_entries = list(db.scalars(select(IntegrationCatalog)).all())
    existing_config_ids = {
        catalog_id for catalog_id in db.scalars(select(IntegrationConfig.catalog_id)).all()
    }
    for catalog in catalog_entries:
        if catalog.id in existing_config_ids:
            continue
        db.add(
            IntegrationConfig(
                catalog_id=catalog.id,
                enabled=False,
                connection_status="not_configured",
                settings_data={},
                notes=None,
            )
        )
    db.commit()
