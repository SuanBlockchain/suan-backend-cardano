from sqlalchemy import BigInteger, Boolean, Column, Enum
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from ..dblib import Base
from .mixins import Timestamp
import uuid

# from routers.api_v1.endpoints.pydantic_schemas import ScriptPurpose


class Projects(Timestamp, Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    suanid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    categoryid = Column(Text, nullable=True)
    status = Column(Boolean, nullable=False)

    # user = relationship("User", back_populates="wallet")
    # transactions = relationship("Transactions", back_populates="wallet")
