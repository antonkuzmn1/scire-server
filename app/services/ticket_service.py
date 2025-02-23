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

    async def get_all_by_admin(self, authorization: str = Header(default=None, description="Bearer token")):
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is required"
            )

        token = authorization.split(" ")[1]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/admins/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                profile = response.json()
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
            user_id = ticket["user_id"]
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.OAUTH_CHECK_URL}/users/{user_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=3.0
                    )
                    response.raise_for_status()
                    user = response.json()
            except httpx.HTTPStatusError as e:
                continue
            except httpx.RequestError as e:
                continue
            except Exception as e:
                continue
            user_company_id = user["company_id"]
            if user_company_id not in admin_companies_ids:
                filtered_tickets.append(ticket)

        return filtered_tickets

    async def get_all_by_user(self, user_id: int):
        filters = [Ticket.user_id == user_id]
        return await super().get_all(*filters)

    async def get_by_id_by_admin(
            self,
            ticket_id: int,
            authorization: str = Header(default=None, description="Bearer token")
    ):
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is required"
            )

        token = authorization.split(" ")[1]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/admins/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                profile = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(401, detail=f"Auth service error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(503, detail=f"Auth service unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(500, detail=f"Unexpected error: {str(e)}")

        admin_companies = profile["companies"]
        admin_companies_ids = [company['id'] for company in admin_companies]

        ticket = await super().get_by_id(ticket_id)
        user_id = ticket["user_id"]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.OAUTH_CHECK_URL}/users/{user_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3.0
                )
                response.raise_for_status()
                user = response.json()
        except httpx.HTTPStatusError as e:
            pass
        except httpx.RequestError as e:
            pass
        except Exception as e:
            pass
        user_company_id = user["company_id"]
        if user_company_id not in admin_companies_ids:
            return ticket
        return None

    async def get_by_id_by_user(self, ticket_id: int, user_id: int):
        filters = [Ticket.user_id == user_id]
        return await super().get_by_id(ticket_id, *filters)
