from src.app.features.auth.application.dtos.auth_dto import (
    AdminLoginResponse,
    LoginRequest,
)
from src.app.features.auth.application.mappers.auth_mapper import to_login_response
from src.app.features.auth.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.email import Email
from src.app.shared.infrastructure.security.account_lockout_service import (
    get_account_lockout_service,
)
from src.app.shared.infrastructure.security.jwt_handler import JWTHandler
from src.app.shared.domain.value_objects.password import Password
from src.app.shared.logging import get_logger, mask_email


class LoginUserUseCase:
    """
    Use case for authenticating users and issuing JWT tokens.

    Implements account lockout to prevent brute-force attacks:
    - Locks account after 5 consecutive failed attempts
    - Progressive lockout duration (15m → 30m → 60m → 120m)
    - Resets on successful login
    """

    def __init__(self, user_repository: UserRepository, jwt_handler: JWTHandler):
        self.user_repository = user_repository
        self.jwt_handler = jwt_handler
        self.lockout_service = get_account_lockout_service()

    async def execute(self, payload: LoginRequest) -> AdminLoginResponse:
        """
        Authenticates user and returns login response with JWT token.

        Args:
            payload: LoginRequest with email and password

        Returns:
            AdminLoginResponse with token and user details

        Raises:
            AccountLockedError: If account is temporarily locked
            InvalidCredentialsError: If credentials are invalid
        """
        email_lower = str(payload.email).lower().strip()
        log = get_logger(__name__)
        is_locked = await self.lockout_service.is_locked_out(email_lower)
        if is_locked:
            lockout_info = await self.lockout_service.get_lockout_info(email_lower)
            # Provide safe defaults if lockout_info is None
            remaining_seconds = (
                lockout_info.get("remaining_seconds", 0) if lockout_info else 0
            )
            remaining_minutes = (
                lockout_info.get("remaining_minutes", 0) if lockout_info else 0
            )
            failed_attempts = (
                lockout_info.get("failed_attempts", 0) if lockout_info else 0
            )

            log.warning(
                f"Login attempt for locked account: "
                f"email={mask_email(email_lower)}, "
                f"remaining_seconds={remaining_seconds}"
            )
            raise AccountLockedError(
                message=f"Account temporarily locked. Try again in {remaining_minutes} minutes.",
                remaining_seconds=remaining_seconds,
                failed_attempts=failed_attempts,
            )

        try:
            user_entity = await self.user_repository.find_by_email(Email(email_lower))

            if not user_entity:
                log.warning(
                    f"Login attempt with non-existent email: "
                    f"{mask_email(email_lower)}"
                )
                # Record attempts for non-existent users to prevent timing-based user enumeration
                await self.lockout_service.record_failed_attempt(email_lower)
                raise InvalidCredentialsError()

            password_valid = Password.verify(
                payload.password,
                user_entity.password_hash,
            )

            if not password_valid:
                failed_attempts = await self.lockout_service.get_failed_attempts(
                    email_lower
                )

                log.warning(
                    f"Failed login attempt — invalid password: "
                    f"user_id={user_entity.id}, "
                    f"email={mask_email(email_lower)}, "
                    f"failed_attempts={failed_attempts + 1}"
                )
                await self.lockout_service.record_failed_attempt(email_lower)
                raise InvalidCredentialsError()

            # Check if account is active
            if not user_entity.is_active:
                log.warning(
                    f"Login attempt on inactive account: "
                    f"user_id={user_entity.id}, "
                    f"email={mask_email(email_lower)}"
                )
                raise InvalidCredentialsError("Account is inactive")

            await self.lockout_service.record_successful_login(email_lower)

            token = self.jwt_handler.create_access_token(
                user_id=str(user_entity.id),
                email=str(user_entity.email),
                role=user_entity.role.value,
            )

            refresh_token = self.jwt_handler.create_refresh_token(
                user_id=str(user_entity.id),
                email=str(user_entity.email),
                role=user_entity.role.value,
            )

            response = to_login_response(
                user_entity,
                access_token=token,
                refresh_token=refresh_token,
                expires_in=self.jwt_handler.expiration_minutes * 60,
            )

            log.info(
                f"User logged in successfully: "
                f"user_id={user_entity.id}, "
                f"email={mask_email(email_lower)}, "
                f"role={user_entity.role.value}"
            )

            return response

        except (InvalidCredentialsError, AccountLockedError):
            raise
        except Exception as e:
            log.error(f"Unexpected error during login: {e}")
            raise
