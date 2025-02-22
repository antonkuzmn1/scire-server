from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db import get_db
from app.services.message_service import MessageService

from app.services.ticket_service import TicketService


async def get_ticket_service(db: AsyncSession = Depends(get_db)) -> TicketService:
    return TicketService(db=db)


async def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    return MessageService(db=db)
