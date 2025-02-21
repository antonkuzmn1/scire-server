from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ticket_repo import TicketRepository
from app.schemas.ticket import TicketOut, TicketFileOut
from app.services.base_service import BaseService


class TicketService(BaseService[TicketRepository]):
    def __init__(self, db: AsyncSession):
        super().__init__(TicketRepository(db), TicketOut, TicketFileOut)

