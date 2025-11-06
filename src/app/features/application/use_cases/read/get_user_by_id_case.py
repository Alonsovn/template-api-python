from src.app.features.domain.repositories.user_repository import UserRepository
from src.shared.utils.uuid_util import convert_str_to_uuid


class GetUserByIdCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: str):

        entity_id = convert_str_to_uuid(user_id)
        return self.user_repository.find_by_id(entity_id)