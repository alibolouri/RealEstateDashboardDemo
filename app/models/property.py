from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, index=True)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bathrooms: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False, index=True)
    square_feet: Mapped[int] = mapped_column(Integer, nullable=False)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    amenities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    listing_agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    listing_agent_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    realtor_id: Mapped[int] = mapped_column(ForeignKey("realtors.id"), nullable=False, index=True)

    realtor: Mapped["Realtor"] = relationship(back_populates="properties")
    leads: Mapped[list["Lead"]] = relationship(back_populates="property")
