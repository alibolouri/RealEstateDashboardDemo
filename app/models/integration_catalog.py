from sqlalchemy import Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IntegrationCatalog(Base):
    __tablename__ = "integration_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    service_name: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sync_scope: Mapped[str] = mapped_column(Text, nullable=False)
    auth_model: Mapped[str] = mapped_column(String(120), nullable=False)
    data_direction: Mapped[str] = mapped_column(String(80), nullable=False)
    readiness_status: Mapped[str] = mapped_column(String(40), nullable=False)
    official_docs_url: Mapped[str] = mapped_column(String(255), nullable=False)
    config_fields: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    config: Mapped["IntegrationConfig | None"] = relationship(
        back_populates="catalog",
        uselist=False,
    )
