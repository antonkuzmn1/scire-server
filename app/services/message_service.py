from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message
from app.repositories.message_repo import MessageRepository
from app.schemas.message import MessageOut, MessageFileOut
from app.services.base_service import BaseService


class MessageService(BaseService[MessageRepository]):
    def __init__(self, db: AsyncSession):
        super().__init__(MessageRepository(db), MessageOut, MessageFileOut)

    async def get_by_ticket_id(self, ticket_id: int):
        filters = [Message.ticket_id == ticket_id, Message.deleted == False]
        return await super().get_all(*filters)
