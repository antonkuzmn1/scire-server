from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ticket, TicketFile
from app.repositories.base_repo import BaseRepository


class TicketRepository(BaseRepository[Ticket, TicketFile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Ticket, TicketFile)

    async def get_all_by_user_id(self, user_id: int) -> List[Ticket]:
        return await self.get_all(self.model.user_id == user_id)

    async def get_tickets_open(self) -> List[Ticket]:
        return await self.get_all(self.model.status == 0)

    async def get_tickets_in_progress(self) -> List[Ticket]:
        return await self.get_all(self.model.status == 1)

    async def get_tickets_closed(self) -> List[Ticket]:
        return await self.get_all(self.model.status == 2)

    async def get_all_by_admin_id(self, admin_id: int) -> List[Ticket]:
        return await self.get_all(self.model.admin_id == admin_id)
