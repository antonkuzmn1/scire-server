# from typing import List, Optional
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from sqlalchemy.exc import SQLAlchemyError
# from app.models import File
# from app.logger import logger
#
#
# class FileRepository:
#     def __init__(self, db: AsyncSession):
#         self.db = db
#
#     async def create_file(self, file_data: dict) -> Optional[File]:
#         try:
#             db_file = File(**file_data)
#             self.db.add(db_file)
#             await self.db.commit()
#             await self.db.refresh(db_file)
#             return db_file
#         except SQLAlchemyError as e:
#             logger.error(f"Error creating file: {e}")
#             await self.db.rollback()
#             return None
#
#     async def get_file(self, file_uuid: str) -> Optional[File]:
#         result = await self.db.execute(select(File).where(File.uuid == file_uuid))
#         return result.scalars().first()
#
#     async def get_all_files(self) -> List[File]:
#         result = await self.db.execute(select(File))
#         return result.scalars().all()
#
#     async def get_all_user_files(self, user_id: str) -> List[File]:
#         result = await self.db.execute(select(File).where(File.user_id == user_id))
#         return result.scalars().all()
#
#     async def delete_file(self, file_uuid: str) -> Optional[File]:
#         try:
#             result = await self.db.execute(select(File).where(File.uuid == file_uuid))
#             db_file = result.scalars().first()
#
#             if db_file:
#                 await self.db.delete(db_file)
#                 await self.db.commit()
#                 return db_file
#
#             return None
#         except SQLAlchemyError as e:
#             logger.error(f"Error deleting file: {e}")
#             await self.db.rollback()
#             return None