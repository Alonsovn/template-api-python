"""
RefreshTokenUseCase - Refresh access token using refresh token.
"""

import jwt

from src.app.features.auth.application.dtos.auth_dto import (
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.domain.value_objects.email import Email
from src.app.shared.infrastructure.security.jwt_handler import JWTHandler
from src.app.shared.infrastructure.security.token_revocation_service import (
    get_token_revocation_service,
)
from src.app.shared.logging import get_logger


class RefreshTokenUseCase:
    """
    Use case for refreshing access tokens using refresh tokens.

    Implements token rotation with single-use refresh tokens:
    - Each refresh generates new access token AND new refresh token
    - Old refresh token is immediately revoked and cannot be reused
    - Prevents token replay attacks and stolen token reuse
    """

    def __init__(self, user_repository: UserRepository, jwt_handler: JWTHandler):
        self.user_repository = user_repository
        self.jwt_handler = jwt_handler

    async def execute(self, payload: RefreshTokenRequest) -> RefreshTokenResponse:
        """
        Refresh access token using refresh token.

        Implements single-use refresh tokens: the old refresh token is
        immediately revoked after use, preventing token reuse attacks.

        Args:
            payload: RefreshTokenRequest with refresh token

        Returns:
            RefreshTokenResponse with new access and refresh tokens

        Raises:
            jwt.ExpiredSignatureError: If refresh token has expired
            jwt.InvalidTokenError: If refresh token is invalid or already used
            ValueError: If user not found
        """
        token_revocation = get_token_revocation_service()
        log = get_logger(__name__)

        try:
            # Decode and validate refresh token first to get user context
            refresh_payload = self.jwt_handler.decode_refresh_token(
                payload.refresh_token
            )

            user_id = str(refresh_payload["sub"])
            email = str(refresh_payload["email"])

            # Check if token has already been used (revoked)
            if await token_revocation.is_revoked(payload.refresh_token):
                log.warning("Attempt to reuse revoked refresh token")
                raise jwt.InvalidTokenError("Refresh token has already been used")

            # Revoke the old refresh token immediately (single-use token)
            await token_revocation.revoke_token(payload.refresh_token)
            log.info("Refresh token revoked")

            # Verify user still exists
            user_entity = await self.user_repository.find_by_email(Email(email))

            if not user_entity:
                log.warning(
                    f"Refresh token used for non-existent user: {email}"
                )
                raise ValueError("User not found")

            # Verify user_id matches
            if str(user_entity.id) != user_id:
                log.warning(
                    f"User ID mismatch in refresh token: {email}"
                )
                raise jwt.InvalidTokenError("Invalid user credentials in token")

            # Generate new access token
            new_access_token = self.jwt_handler.create_access_token(
                user_id=str(user_entity.id),
                email=str(user_entity.email),
                role=user_entity.role.value,
            )

            # Generate new refresh token (token rotation)
            new_refresh_token = self.jwt_handler.create_refresh_token(
                user_id=str(user_entity.id),
                email=str(user_entity.email),
                role=user_entity.role.value,
            )

            log.info(
                f"Tokens refreshed successfully: "
                f"user_id={user_entity.id}"
            )

            return RefreshTokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=self.jwt_handler.expiration_minutes * 60,
            )

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            raise
        except Exception as e:
            log.error(f"Unexpected error in RefreshTokenUseCase: {e}")
            raise
