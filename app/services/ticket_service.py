import httpx
from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ticket
from app.repositories.ticket_repo import TicketRepository
from app.schemas.ticket import TicketOut, TicketFileOut
from app.services.base_service import BaseService
from app.settings import settings


class TicketService(BaseService[TicketRepository]):
    def __init__(self, db: AsyncSession):
        super().__init__(TicketRepository(db), TicketOut, TicketFileOut)

    async def get_all_by_admin(self, token: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/admins/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                profile = response.json()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/users/",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                users = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(401, detail=f"Auth service error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(503, detail=f"Auth service unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(500, detail=f"Unexpected error: {str(e)}")

        admin_companies = profile["companies"]
        admin_companies_ids = [company['id'] for company in admin_companies]

        all_tickets = await super().get_all()
        filtered_tickets = []
        for ticket in all_tickets:
            user_id = ticket.user_id
            user = next((user for user in users if user["id"] == user_id), None)
            if user:
                user_company_id = user["company_id"]
                if user_company_id in admin_companies_ids:
                    filtered_tickets.append(ticket)

        return filtered_tickets

    async def get_all_by_user(self, user_id: int):
        filters = [Ticket.user_id == user_id]
        return await super().get_all(*filters)

    async def get_by_id_by_admin(
            self,
            ticket_id: int,
            token: str,
    ):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/admins/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                profile = response.json()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/users/",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                users = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(401, detail=f"Auth service error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(503, detail=f"Auth service unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(500, detail=f"Unexpected error: {str(e)}")

        admin_companies = profile["companies"]
        admin_companies_ids = [company['id'] for company in admin_companies]

        ticket = await super().get_by_id(ticket_id)
        user_id = ticket.user_id
        user = next((user for user in users if user["id"] == user_id), None)
        if user:
            user_company_id = user["company_id"]
            if user_company_id in admin_companies_ids:
                return ticket
        return None

    async def get_by_id_by_user(self, ticket_id: int, user_id: int):
        filters = [Ticket.user_id == user_id]
        return await super().get_by_id(ticket_id, *filters)

    async def get_files_by_ticket_by_admin(self, ticket_id: int, token: str):
        ticket = await self.get_by_id_by_admin(ticket_id, token)
        if not ticket:
            return []
        return await super().get_files_by_item_id(ticket.id)

    async def get_files_by_ticket_by_user(self, ticket_id: int, user_id: int):
        ticket = await self.get_by_id_by_user(ticket_id, user_id)
        if not ticket:
            return []
        return await super().get_files_by_item_id(ticket.id)