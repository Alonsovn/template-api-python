import hashlib
import os
import secrets
from datetime import datetime, timedelta

from src.app.config.app_config import AppConfig
from src.app.features.auth.application.dtos.auth_dto import ForgotPasswordResponse
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.email import Email
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class ForgotPasswordUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.token_expire_minutes = int(
            AppConfig.instance().get_config(
                "security.password_reset_token_expire_minutes", 30
            )
        )

    async def execute(self, email: str) -> ForgotPasswordResponse:
        """Generate a password reset token for the given email.

        Always returns a success response to prevent user enumeration.
        The reset token is hashed before storage.
        In non-production environments, the raw token is logged for development.
        """
        try:
            email_vo = Email(email.lower().strip())
            user_entity = await self.user_repository.find_by_email(email_vo)

            if not user_entity:
                # Don't disclose whether the email exists — return generic success
                log.info(f"Password reset requested for non-existent email: {email_vo}")
                return ForgotPasswordResponse(
                    message="If an account with that email exists, "
                    "a password reset link has been sent."
                )

            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            expires_at = datetime.now() + timedelta(minutes=self.token_expire_minutes)

            user_entity.set_password_reset_token(token_hash, expires_at)
            await self.user_repository.update(user_entity)

            log.info(f"Password reset token generated for email: {email_vo}")

            # In non-production envs, log the raw token for dev convenience
            env = os.getenv("APP_ENV", "local")
            if env in ("local", "dev", "test"):
                log.info(f"[DEV] Password reset token: {raw_token}")

            return ForgotPasswordResponse(
                message="If an account with that email exists, "
                "a password reset link has been sent."
            )

        except ValueError:
            raise
        except Exception as e:
            log.error(f"Unexpected error in ForgotPasswordUseCase: {str(e)}")
            raise
