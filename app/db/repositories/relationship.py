from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.relationship import Relationship
from app.db.repositories.base import CRUDRepository


class RelationshipRepository(CRUDRepository[Relationship, int]):
    pass