from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageFileBase(BaseModel):
    item_id: int
    file_uuid: str
    file_name: str
    file_size: int


class MessageFileCreate(MessageFileBase):
    pass


class MessageFileUpdate(MessageFileBase):
    pass


class MessageFileOut(MessageFileBase):
    pass


class MessageBase(BaseModel):
    text: str
    user_id: int
    admin_id: Optional[int] = None
    ticket_id: int
    admin_connected: bool = False
    admin_disconnected: bool = False
    in_progress: bool = False
    solved: bool = False


class MessageCreate(MessageBase):
    pass


class MessageUpdate(MessageBase):
    pass


class MessageOut(MessageBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    files: list[MessageFileOut] = []

    class Config:
        from_attributes = True
