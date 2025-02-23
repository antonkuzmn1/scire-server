from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import verify_token
from app.dependencies.services import get_message_service
from app.schemas.message import MessageOut
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("/{ticket_id}", response_model=List[MessageOut])
async def get_messages_by_ticket_id(
        ticket_id: int,
        account: dict = Depends(verify_token),
        service: MessageService = Depends(get_message_service)
):
    if account["role"] == "admin" or account["role"] == "user":
        return await service.get_by_ticket_id(ticket_id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )
