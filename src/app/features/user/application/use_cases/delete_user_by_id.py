from src.app.features.user.domain.exceptions.user_exceptions import (
    UserNotFoundError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.entity_id import EntityId
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class DeleteUserByIdUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> bool:

        try:
            user_obj_id = EntityId.from_string(user_id)

            deleting_user = await self.user_repository.delete(user_obj_id)

            if not deleting_user:
                log.warning(f"User not found for deletion with ID: {user_id}")
                raise UserNotFoundError(user_id)

            return True

        except (ValueError, UserNotFoundError):
            raise
        except Exception as e:
            log.error(
                f"Unexpected error during delete user by ID for {user_id}: {str(e)}"
            )
            raise
