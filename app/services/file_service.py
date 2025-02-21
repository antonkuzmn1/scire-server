# import os
# from uuid import uuid4
# from pathlib import Path
# from typing import Optional, List
# import aiofiles
# from fastapi import UploadFile, HTTPException, status
#
# from app.repositories.file_repo import FileRepository
# from app.schemas.file import FileOut, FileCreate
# from app.logger import logger
#
#
# class FileService:
#     def __init__(self, repository: FileRepository, upload_dir: str):
#         self.repository = repository
#         self.upload_dir = Path(upload_dir)
#         self.upload_dir.mkdir(parents=True, exist_ok=True)
#
#     async def save_upload_file(self, file: UploadFile, user_id: int) -> FileOut:
#         file_uuid = str(uuid4())
#         file_location = self.upload_dir / file_uuid
#
#         try:
#             async with aiofiles.open(file_location, "wb") as buffer:
#                 content = await file.read()
#                 await buffer.write(content)
#
#             file_data = FileCreate(
#                 name=file.filename,
#                 size=len(content),
#                 user_id=user_id
#             )
#
#             db_file = await self.repository.create_file({
#                 **file_data.model_dump(),
#                 "uuid": file_uuid
#             })
#
#             if not db_file:
#                 raise HTTPException(
#                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     detail="Failed to create file record"
#                 )
#
#             return FileOut.model_validate(db_file)
#
#         except Exception as e:
#             logger.error(f"File upload error: {str(e)}")
#             await self._cleanup_failed_upload(file_location)
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"File upload failed: {str(e)}"
#             )
#
#         finally:
#             await file.close()
#
#     async def get_file_path(self, file_uuid: str) -> Optional[Path]:
#         file_path = self.upload_dir / file_uuid
#         return file_path if await self._check_file_exists(file_path) else None
#
#     async def delete_file(self, file_uuid: str) -> bool:
#         try:
#             file_path = self.upload_dir / file_uuid
#             db_file = await self.repository.delete_file(file_uuid)
#
#             if db_file and await self._check_file_exists(file_path):
#                 os.remove(file_path)
#
#             return True
#         except Exception as e:
#             logger.error(f"File deletion error: {str(e)}")
#             return False
#
#     async def get_user_files(self, user_id: str) -> List[FileOut]:
#         db_files = await self.repository.get_all_user_files(user_id)
#         return [FileOut.model_validate(f) for f in db_files]
#
#     async def get_all_files(self) -> List[FileOut]:
#         db_files = await self.repository.get_all_files()
#         return [FileOut.model_validate(f) for f in db_files]
#
#     async def verify_file_access(self, file_uuid: str, user_id: str, roles: List[str]) -> FileOut:
#         db_file = await self.repository.get_file(file_uuid)
#
#         if not db_file:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="File not found"
#             )
#
#         if "owner" in roles or "admin" in roles:
#             return FileOut.model_validate(db_file)
#
#         if str(db_file.user_id) != user_id:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Access denied"
#             )
#
#         return FileOut.model_validate(db_file)
#
#     @staticmethod
#     async def _check_file_exists(path: Path) -> bool:
#         try:
#             return path.exists()
#         except OSError:
#             return False
#
#     @staticmethod
#     async def _cleanup_failed_upload(path: Path):
#         try:
#             if await FileService._check_file_exists(path):
#                 os.remove(path)
#         except OSError as e:
#             logger.error(f"Failed to clean up file: {str(e)}")