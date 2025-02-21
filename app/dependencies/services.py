# from sqlalchemy.ext.asyncio import AsyncSession
# from fastapi import Depends
#
# from app.db import get_db
# from app.repositories.file_repo import FileRepository
# from app.services.file_service import FileService
# from app.settings import settings
#
#
# async def get_file_service(db: AsyncSession = Depends(get_db)) -> FileService:
#     return FileService(
#         repository=FileRepository(db),
#         upload_dir=settings.UPLOAD_DIR
#     )
