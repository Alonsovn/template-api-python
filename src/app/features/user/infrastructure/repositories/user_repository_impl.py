from typing import Optional

from sqlalchemy import func, select
import sqlalchemy.exc

from src.app.features.user.domain.entities.user_entity import UserEntity
from src.app.features.user.domain.exceptions.user_exceptions import (
    UserAlreadyExistsError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.features.user.infrastructure.models.user_model import UserModel
from src.app.features.user.infrastructure.mappers.user_model_mapper import (
    UserModelMapper,
)
from src.app.shared.domain.value_objects.email import Email
from src.app.shared.domain.value_objects.entity_id import EntityId

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.shared.logging import get_logger

log = get_logger(__name__)


class DatabaseConnectionError(Exception):
    """Custom exception to indicate database connection errors."""

    pass


class UserRepositoryImpl(UserRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def find_by_id(self, entity_id: EntityId) -> Optional[UserEntity]:
        try:
            log.info(f"start get user by id: {entity_id.value}")
            user_model: Optional[UserModel] = await self.db_session.get(
                UserModel, entity_id.value
            )
            if user_model is None:
                log.info(f"user by id {entity_id.value} not found")
                return None
            log.info(f"completed get user by id {entity_id.value}")
            return UserModelMapper.to_entity(user_model)

        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while finding user by id: {entity_id.value}. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            log.error(
                f"Error finding user by id: {entity_id.value} Exceptions: {str(e)}"
            )
            raise

    async def find_by_email(self, email: Email) -> Optional[UserEntity]:
        try:
            result = await self.db_session.execute(
                select(UserModel).where(UserModel.email == email.value)
            )
            user_model = result.scalar_one_or_none()
            if user_model is None:
                log.info(f"User with email {email.value} not found.")
                return None
            log.info(f"User with email {email.value} found.")
            return UserModelMapper.to_entity(user_model)

        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while finding user by email: {email.value}. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            log.error(f"Error finding user by email: {email.value}. Error: {str(e)}")
            raise

    async def find_by_reset_token_hash(self, token_hash: str) -> Optional[UserEntity]:
        try:
            result = await self.db_session.execute(
                select(UserModel).where(
                    UserModel.password_reset_token_hash == token_hash
                )
            )
            user_model = result.scalar_one_or_none()
            if user_model is None:
                log.info("User with given reset token hash not found.")
                return None
            log.info("User found by reset token hash.")
            return UserModelMapper.to_entity(user_model)

        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while finding user by reset token. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            log.error(f"Error finding user by reset token: {str(e)}")
            raise

    async def find_all(self, skip: int = 0, limit: int = 20) -> list[UserEntity]:
        try:
            result = await self.db_session.execute(
                select(UserModel)
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.created_at.desc())
            )
            models = result.scalars().all()
            return [UserModelMapper.to_entity(m) for m in models]
        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while listing users. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            log.error(f"Error listing users: {str(e)}")
            raise

    async def count(self) -> int:
        try:
            result = await self.db_session.execute(select(func.count(UserModel.id)))
            return result.scalar_one()
        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while counting users. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            log.error(f"Error counting users: {str(e)}")
            raise

    async def save(self, user: UserEntity) -> UserEntity:
        try:
            result = await self.db_session.execute(
                select(UserModel).where(UserModel.email == user.email.value)
            )
            if result.scalar_one_or_none():
                log.warning(f"[save] User with email {user.email} already exists")
                raise UserAlreadyExistsError(user.email.value)

            user_model = UserModelMapper.to_model(user)
            self.db_session.add(user_model)
            await self.db_session.commit()
            await self.db_session.refresh(user_model)

            log.info(f"[save] User persisted successfully. id={user_model.id}")
            return UserModelMapper.to_entity(user_model)

        except sqlalchemy.exc.IntegrityError as e:
            await self.db_session.rollback()
            log.error(
                f"[save] IntegrityError while saving user with email {user.email}: {e}"
            )
            raise UserAlreadyExistsError(user.email.value) from e

        except sqlalchemy.exc.OperationalError as db_error:
            await self.db_session.rollback()
            log.error(
                f"Database connection error while saving user: {user.email}. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error

        except Exception as e:
            await self.db_session.rollback()
            log.error(
                f"[save] Unexpected error while saving user with email {user.email}: {e}"
            )
            raise

    async def update(self, entity: UserEntity) -> Optional[UserEntity]:
        try:
            user_model = await self.db_session.get(UserModel, entity.id.value)

            if user_model is None:
                log.warning(f"User with id {entity.id.value} not found for update.")
                return None

            mapped = UserModelMapper.to_model(entity)
            user_model.email = mapped.email
            user_model.first_name = mapped.first_name
            user_model.last_name = mapped.last_name
            user_model.role = mapped.role
            user_model.is_active = mapped.is_active
            user_model.password_hash = mapped.password_hash
            user_model.password_reset_token_hash = mapped.password_reset_token_hash
            user_model.password_reset_expires_at = mapped.password_reset_expires_at

            await self.db_session.commit()
            await self.db_session.refresh(user_model)

            log.info(f"User with id {entity.id.value} updated successfully.")
            return UserModelMapper.to_entity(user_model)

        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while updating user {entity.id.value}. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error

        except Exception as e:
            await self.db_session.rollback()
            log.error(f"Error updating user {entity.id.value}: {str(e)}")
            raise

    async def delete(self, entity_id: EntityId) -> bool:
        try:
            existing_user = await self.db_session.get(UserModel, entity_id.value)
            if not existing_user:
                log.info(f"User with id {entity_id.value} not found for deletion.")
                return False
            await self.db_session.delete(existing_user)
            await self.db_session.commit()
            log.info(f"User with id {entity_id.value} successfully deleted.")
            return True
        except sqlalchemy.exc.OperationalError as db_error:
            log.error(
                f"Database connection error while deleting user: {entity_id.value}. Error: {str(db_error)}"
            )
            raise DatabaseConnectionError(
                "Failed to connect to the database."
            ) from db_error
        except Exception as e:
            await self.db_session.rollback()
            log.error(f"Error deleting user: {entity_id.value} Exceptions: {str(e)}")
            raise
