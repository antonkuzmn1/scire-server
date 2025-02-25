from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.dependencies.auth import verify_token
from app.dependencies.services import get_ticket_service
from app.schemas.ticket import TicketOut, TicketFileOut
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/", response_model=List[TicketOut])
async def get_all_tickets(
        account: dict = Depends(verify_token),
        service: TicketService = Depends(get_ticket_service),
        authorization: str = Header(...),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header"
        )

    token = authorization.removeprefix("Bearer ").strip()

    if account["role"] == "admin":
        return await service.get_all_by_admin(token)

    if account["role"] == "user":
        return await service.get_all_by_user(account["id"])

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


@router.get("/{ticket_id}", response_model=Optional[TicketOut])
async def get_ticket_by_id(
        ticket_id: int,
        account: dict = Depends(verify_token),
        service: TicketService = Depends(get_ticket_service),
        authorization: str = Header(...),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header"
        )

    token = authorization.removeprefix("Bearer ").strip()

    if account["role"] == "admin":
        return await service.get_by_id_by_admin(ticket_id, token)

    if account["role"] == "user":
        return await service.get_by_id_by_user(ticket_id, account["id"])

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


@router.get("/{ticket_id}/files", response_model=List[TicketFileOut])
async def get_ticket_files_by_ticket_id(
        ticket_id: int,
        account: dict = Depends(verify_token),
        service: TicketService = Depends(get_ticket_service),
        authorization: str = Header(...),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header"
        )

    token = authorization.removeprefix("Bearer ").strip()

    if account["role"] == "admin":
        return await service.get_files_by_ticket_by_admin(ticket_id, token)

    if account["role"] == "user":
        return await service.get_files_by_ticket_by_user(ticket_id, account["id"])

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )