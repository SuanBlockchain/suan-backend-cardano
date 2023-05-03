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
    name = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    sector = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    owner = Column(Text, nullable=True)
    uid = Column(Text, nullable=True)
    kind = Column(Text, nullable=False)
    asset_type = Column(Text, nullable=False)
    version_id = Column(Text, nullable=False)

    # user = relationship("User", back_populates="wallet")
    # transactions = relationship("Transactions", back_populates="wallet")
