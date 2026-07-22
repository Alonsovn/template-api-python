from src.app.features.user.application.mappers.user_dto_mapper import (
    to_user_response,
    UserResponse,
)
from src.app.features.user.domain.exceptions.user_exceptions import (
    UserNotFoundError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.entity_id import EntityId
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class GetUserByIdUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> UserResponse:
        try:
            user_obj_id = EntityId.from_string(user_id)

            existing_user = await self.user_repository.find_by_id(user_obj_id)

            if not existing_user:
                log.warning(f"User not found with ID: {user_id}")
                raise UserNotFoundError(user_id)

            response_dto = to_user_response(existing_user)

            return response_dto

        except ValueError:
            raise
        except UserNotFoundError:
            raise
        except Exception:
            raise
