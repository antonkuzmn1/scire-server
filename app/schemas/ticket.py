from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.message import MessageOut


class TicketFileBase(BaseModel):
    item_id: int
    file_uuid: str
    file_name: str
    file_size: int


class TicketFileCreate(TicketFileBase):
    pass


class TicketFileUpdate(TicketFileBase):
    pass


class TicketFileOut(TicketFileBase):
    pass


class TicketBase(BaseModel):
    title: str
    description: str
    status: int = 0
    user_id: int
    admin_id: Optional[int] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(TicketBase):
    pass


class TicketOut(TicketBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: list[MessageOut] = []
    files: list[TicketFileOut] = []

    class Config:
        from_attributes = True
