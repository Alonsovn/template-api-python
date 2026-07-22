from src.app.features.user.application.dtos.user_dto import (
    UserResponse,
    UserUpdateRequest,
)
from src.app.features.user.application.mappers.user_dto_mapper import (
    to_user_response,
)
from src.app.features.user.domain.exceptions.user_exceptions import (
    UserNotFoundError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.entity_id import EntityId
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class UpdateUserByIdUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, user_id: str, payload: UserUpdateRequest) -> UserResponse:
        try:
            user_obj_id = EntityId.from_string(user_id)

            existing_user = await self.user_repository.find_by_id(user_obj_id)

            if not existing_user:
                log.warning(f"User not found for update with ID: {user_id}")
                raise UserNotFoundError(user_id)

            existing_user.update_details(
                email=payload.email,
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
                role=payload.role,
                is_active=payload.is_active,
            )

            updated_user = await self.user_repository.update(existing_user)

            if not updated_user:
                log.warning(f"User with id {user_id} not found for update.")
                raise UserNotFoundError(user_id)

            response_dto = to_user_response(updated_user)

            log.info(f"User updated successfully: {updated_user.id}")
            return response_dto

        except ValueError:
            raise
        except UserNotFoundError:
            raise
        except Exception as e:
            log.error(f"Unexpected error in UpdateUserByIdUseCase: {str(e)}")
            raise
