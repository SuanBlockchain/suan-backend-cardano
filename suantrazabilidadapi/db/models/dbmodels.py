from sqlalchemy import BigInteger, Boolean, Column, Enum
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from ..dblib import Base
from .mixins import Timestamp

# from routers.api_v1.endpoints.pydantic_schemas import ScriptPurpose


class Projects(Timestamp, Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    suanid = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    categoryid = Column(Text, nullable=True)
    status = Column(Text, nullable=False)

    # user = relationship("User", back_populates="wallet")
    # transactions = relationship("Transactions", back_populates="wallet")

class Kobo_forms(Base):
    __tablename__ = "kobo_forms"

    id = Column(Integer, primary_key=True)
    koboform_id = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    organization = Column(Text, nullable=True)
    country = Column(Text, nullable=True)
    kind = Column(Text, nullable=True)
    asset_type = Column(Text, nullable=True)
    deployment_active = Column(Text, nullable=True)
    deployment_count = Column(Integer, nullable=True)
    owner_username = Column(Text, nullable=True)
    has_deployment = Column(Boolean, nullable=False)
    status = Column(Text, nullable=True)