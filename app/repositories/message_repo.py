from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, MessageFile
from app.repositories.base_repo import BaseRepository


class MessageRepository(BaseRepository[Message, MessageFile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Message, MessageFile)

    async def get_all_by_ticket_id(self, ticket_id: int) -> List[Message]:
        return await self.get_all(self.model.ticket_id == ticket_id)
