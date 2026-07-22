from src.app.features.user.application.dtos.user_dto import (
    UserCreateRequest,
    UserResponse,
)
from src.app.features.user.application.mappers.user_dto_mapper import (
    to_user_entity,
    to_user_response,
)
from src.app.features.user.domain.exceptions.user_exceptions import (
    UserAlreadyExistsError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.password import Password
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, payload: UserCreateRequest) -> UserResponse:
        try:
            # Validate and hash password via domain value object
            password_vo = Password(payload.password)
            password_hash = password_vo.hash()

            new_user_entity = to_user_entity(payload, password_hash)

            existing_user = await self.user_repository.find_by_email(
                new_user_entity.email
            )

            if existing_user:
                log.warning(
                    f"Duplicate user creation attempt with email: {new_user_entity.email}"
                )
                raise UserAlreadyExistsError(str(new_user_entity.email))

            created_user = await self.user_repository.save(new_user_entity)

            response_dto = to_user_response(created_user)

            log.info(f"User created successfully: {created_user.id}")
            return response_dto

        except (ValueError, UserAlreadyExistsError):
            raise
        except Exception as e:
            log.error(f"Unexpected error in CreateUserUseCase: {str(e)}")
            raise
