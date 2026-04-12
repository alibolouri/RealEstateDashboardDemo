from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_email: Mapped[str] = mapped_column(String(120), nullable=False)
    user_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    desired_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    desired_budget: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    assigned_realtor_id: Mapped[int] = mapped_column(ForeignKey("realtors.id"), nullable=False)
    fixed_contact_number: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="routed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    property: Mapped["Property | None"] = relationship(back_populates="leads")
    assigned_realtor: Mapped["Realtor"] = relationship(back_populates="leads")
