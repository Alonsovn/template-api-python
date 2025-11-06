from sqlalchemy import Column, String, Enum, Text, Boolean
from src.shared.infrastructure.models.base_model import BaseModel


class UserModel(BaseModel):
    """
    SQLAlchemy model for the User table.
    Maps the UserEntity to a PostgreSQL database table.
    """
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

