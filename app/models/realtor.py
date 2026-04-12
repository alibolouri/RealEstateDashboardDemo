from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Realtor(Base):
    __tablename__ = "realtors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    cities_covered: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    properties: Mapped[list["Property"]] = relationship(back_populates="realtor")
    leads: Mapped[list["Lead"]] = relationship(back_populates="assigned_realtor")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "specialty": self.specialty,
            "cities_covered": self.cities_covered,
        }
