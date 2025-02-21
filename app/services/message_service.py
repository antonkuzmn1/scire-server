from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.message_repo import MessageRepository
from app.schemas.message import MessageOut, MessageFileOut
from app.services.base_service import BaseService


class MessageService(BaseService[MessageRepository]):
    def __init__(self, db: AsyncSession):
        super().__init__(MessageRepository(db), MessageOut, MessageFileOut)

