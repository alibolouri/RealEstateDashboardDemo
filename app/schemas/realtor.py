from app.schemas.common import ORMBaseModel


class RealtorResponse(ORMBaseModel):
    id: int
    name: str
    phone: str
    email: str
    specialty: str
    cities_covered: list[str]
