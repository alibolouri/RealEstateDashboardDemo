from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("integration_catalog.id"), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_configured")
    settings_data: Mapped[dict[str, str | bool | int]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    catalog: Mapped["IntegrationCatalog"] = relationship(back_populates="config")
