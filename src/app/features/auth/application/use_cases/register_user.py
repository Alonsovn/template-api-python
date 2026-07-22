"""
RegisterUserUseCase - Public registration with auto-login.

Following API spec requirements:
- Public endpoint (no auth required)
- Default role: viewer
- Returns JWT token (auto-login behavior)
- Returns AdminLoginResponse (same format as login)
"""

from src.app.features.auth.application.dtos.auth_dto import AdminLoginResponse
from src.app.features.auth.application.mappers.auth_mapper import to_login_response
from src.app.features.user.application.dtos.user_dto import UserCreateRequest
from src.app.features.user.application.mappers.user_dto_mapper import to_user_entity
from src.app.features.user.domain.exceptions.user_exceptions import (
    UserAlreadyExistsError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.infrastructure.security.jwt_handler import JWTHandler
from src.app.shared.domain.value_objects.password import Password
from src.app.shared.logging import get_logger


class RegisterUserUseCase:
    """
    Use case for user registration with auto-login.

    Creates a new user with default viewer role and returns JWT token
    for immediate authentication (auto-login behavior).
    """

    def __init__(self, user_repository: UserRepository, jwt_handler: JWTHandler):
        self.user_repository = user_repository
        self.jwt_handler = jwt_handler

    async def execute(self, payload: UserCreateRequest) -> AdminLoginResponse:
        """
        Register new user and return JWT token (auto-login).

        Args:
            payload: User registration data (email, password, displayName)

        Returns:
            AdminLoginResponse with JWT token and user details

        Raises:
            UserAlreadyExistsError: If email already exists
            ValueError: If validation fails
        """
        log = get_logger(__name__)

        try:
            password_hash = Password(payload.password).hash()

            new_user_entity = to_user_entity(payload, password_hash)

            # Enforce email uniqueness constraint at application layer
            existing_user = await self.user_repository.find_by_email(
                new_user_entity.email
            )

            if existing_user:
                log.warning(
                    f"Registration attempt with existing email: "
                    f"{new_user_entity.email}"
                )
                raise UserAlreadyExistsError(str(new_user_entity.email))

            created_user = await self.user_repository.save(new_user_entity)

            # Handle race condition where another request created the user between check and save
            if created_user is None:
                log.warning(
                    f"Race condition during registration: "
                    f"{new_user_entity.email}"
                )
                raise UserAlreadyExistsError(str(new_user_entity.email))

            token = self.jwt_handler.create_access_token(
                user_id=str(created_user.id.value),
                email=str(created_user.email.value),
                role=created_user.role.value,
            )

            refresh_token = self.jwt_handler.create_refresh_token(
                user_id=str(created_user.id.value),
                email=str(created_user.email.value),
                role=created_user.role.value,
            )

            response = to_login_response(
                created_user,
                access_token=token,
                refresh_token=refresh_token,
                expires_in=self.jwt_handler.expiration_minutes * 60,
            )

            log.info(
                f"User registered successfully: user_id={created_user.id.value}"
            )
            return response

        except (ValueError, UserAlreadyExistsError):
            raise
        except Exception as e:
            log.error(f"Unexpected error in RegisterUserUseCase: {e}")
            raise
