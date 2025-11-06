from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.features.domain.entities.user_entity import UserEntity
from src.app.features.domain.repositories.user_repository import UserRepository
from src.app.features.domain.value_objects.email import Email
from src.app.features.infrastructure.models.user_model import UserModel
from src.shared.domain.repositories.base_repository import ID, T


class UserRepositoryImpl(UserRepository):

    def __init__(self, session: AsyncSession):
        """
        Initializes the UserRepositoryImpl with a SQLAlchemy AsyncSession.

        Args:
            session (AsyncSession): The SQLAlchemy session to use for database operations.
        """
        self.session = session

    async def find_by_id(self, entity_id: ID) -> Optional[T]:

        user_model: Optional[UserModel] = await self.session.get(UserModel, entity_id)

    async def find_by_email(self, email: Email) -> Optional[UserEntity]:
        pass

    async def find_by_name(self, record: str) -> Optional[UserEntity]:
        pass

    async def save(self, entity: T) -> T:
        pass

    async def find_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        pass

    async def exists(self, entity_id: ID) -> bool:
        pass

    async def update(self, entity: T) -> Optional[T]:
        pass

    async def delete(self, entity_id: ID) -> bool:
        pass
