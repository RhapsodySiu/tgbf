from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

T = TypeVar("T")
ID = TypeVar("ID") # Primary key type

class CRUDRepository(Generic[T, ID]):
    """Generic CRUD repository base class for SQLAlchemy models."""

    def __init__(self, model: Type[T]):
        self.model = model

    async def create(self, db: AsyncSession, data: dict) -> T:
        """Insert a new record."""
        try:
            obj = self.model(**data)
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            return obj
        except SQLAlchemyError as e:
            await db.rollback()
            raise RuntimeError(f"Error creating {self.model.__name__}: {e}")
    
    async def get_by_id(self, db: AsyncSession, id: ID) -> Optional[T]:
        """Retrieve a record by primary key."""
        return await db.get(self.model, id)
    
    async def get_all(self, db: AsyncSession) -> List[T]:
        """Retrieve all records."""
        result = await db.execute(select(self.model))
        return list(result.scalars().all())
    
    async def update(self, db: AsyncSession, id: ID, data: dict) -> Optional[T]:
        """Update a record by primary key"""
        obj = await self.get_by_id(db, id)
        if not obj:
            return None
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
            
        try:
            await db.commit()
            await db.refresh(obj)
            return obj
        except SQLAlchemyError as e:
            await db.rollback()
            raise RuntimeError(f"Error updating {self.model.__name__}: {e}")
        
    async def delete(self, db: AsyncSession, id: ID) -> bool:
        """Delete a record by primary key."""
        obj = await self.get_by_id(db, id)
        if not obj:
            return False
        try:
            await db.delete(obj)
            await db.commit()
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            raise RuntimeError(f"Error deleting {self.model.__name__}: {e}")