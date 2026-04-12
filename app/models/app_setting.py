from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    fixed_contact_number: Mapped[str] = mapped_column(String(32), nullable=False)
    default_realtor_id: Mapped[int] = mapped_column(ForeignKey("realtors.id"), nullable=False)
    chat_result_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    default_desired_city_fallback: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dashboard_density: Mapped[str] = mapped_column(String(20), nullable=False, default="comfortable")
    dashboard_table_page_size: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    feature_integrations_panel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_lead_routing_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_catalog_visibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    default_realtor: Mapped["Realtor"] = relationship()
