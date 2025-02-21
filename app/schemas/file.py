# from pydantic import BaseModel
# from datetime import datetime
# from typing import Optional
#
#
# class FileBase(BaseModel):
#     name: str
#     size: int
#     user_id: int
#
# class FileCreate(FileBase):
#     pass
#
# class FileOut(FileBase):
#     uuid: str
#     created_at: Optional[datetime] = None
#     updated_at: Optional[datetime] = None
#
#     class Config:
#         from_attributes = True