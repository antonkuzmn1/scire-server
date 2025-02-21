from typing import Type, TypeVar, Generic, Optional, List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.logger import logger
from app.models import Base, TicketFile

T = TypeVar("T", bound=Base)
D = TypeVar("D", bound=Base)


class BaseRepository(Generic[T, D]):
    def __init__(self, db: AsyncSession, model: Type[T], model_file: Type[D]):
        self.db = db
        self.model = model
        self.model_file = model_file

    async def get_all(self, *filters) -> List[T]:
        base_filters = [self.model.deleted.is_(False)]
        if filters:
            base_filters.extend(filters)
        stmt = select(self.model).where(*base_filters).distinct()
        return list((await self.db.scalars(stmt)).all())

    async def get_by_id(self, item_id: int, *filters) -> Optional[T]:
        base_filters = [self.model.id == item_id, self.model.deleted.is_(False)]
        if filters:
            base_filters.extend(filters)
        stmt = select(self.model).where(*base_filters)
        return await self.db.scalar(stmt)

    async def create(self, item_data: dict) -> Optional[T]:
        logger.warning("BASE_REPO: Attempt to create something")
        item = self.model(**item_data)
        try:
            self.db.add(item)
            await self.db.commit()
            await self.db.refresh(item)
        except SQLAlchemyError as e:
            logger.error(f"Error creating item: {e}")
            await self.db.rollback()
            return None
        return item

    async def update(self, item_id: int, item_data: dict) -> Optional[T]:
        logger.warning("BASE_REPO: Attempt to update something")
        item = await self.get_by_id(item_id)
        if not item:
            return None

        for key, value in item_data.items():
            setattr(item, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(item)
        except SQLAlchemyError as e:
            logger.error(f"Error updating item: {e}")
            await self.db.rollback()
            return None

        return item

    async def delete(self, item_id: int) -> Optional[T]:
        item = await self.get_by_id(item_id)
        if not item:
            return None

        item.deleted = True

        try:
            await self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error deleting item: {e}")
            await self.db.rollback()
            return None

        return item

    async def get_files_by_item_id(self, item_id: int) -> List[D]:
        base_filters = [self.model_file.item_id == item_id]
        stmt = select(self.model).where(*base_filters)
        return await self.db.scalar(stmt)

    async def add_file(self, file_data: dict) -> Optional[D]:
        file = self.model_file(**file_data)
        try:
            self.db.add(file)
            await self.db.commit()
            await self.db.refresh(file)
        except SQLAlchemyError as e:
            logger.error(f"Error adding file: {e}")
            await self.db.rollback()
            return None
        return file
