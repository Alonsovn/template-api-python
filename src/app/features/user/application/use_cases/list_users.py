from src.app.features.user.application.dtos.user_dto import UserResponse
from src.app.features.user.application.mappers.user_dto_mapper import (
    to_user_response,
)
from src.app.features.user.domain.repositories.user_repository import UserRepository
from src.app.shared.application.dtos.pagination_dto import PaginatedResponse
from src.app.shared.logging import get_logger

log = get_logger(__name__)


class ListUsersUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(
        self, skip: int = 0, limit: int = 20
    ) -> PaginatedResponse[UserResponse]:
        try:
            total = await self.user_repository.count()
            page = (skip // limit) + 1 if limit > 0 else 1
            users = await self.user_repository.find_all(skip=skip, limit=limit)

            items = [to_user_response(u) for u in users]

            log.info(f"Listed {len(items)} users (total: {total}, page: {page}).")
            return PaginatedResponse(
                total=total,
                page=page,
                per_page=limit,
                items=items,
            )

        except Exception as e:
            log.error(f"Unexpected error in ListUsersUseCase: {str(e)}")
            raise
