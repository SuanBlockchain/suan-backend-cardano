from sqlalchemy import Boolean, Column
from sqlalchemy import Integer, Text

from ..dblib import Base


class TokenAccess(Base):
    __tablename__ = "claim_token_access"

    id = Column(Integer, primary_key=True, index=True)
    requester = Column(Text, nullable=False)
    valid = Column(Boolean, nullable=False)
    utxo = Column(Text, nullable=False)
    error = Column(Boolean, nullable=False)
    processed = Column(Boolean, nullable=False)
    txid = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
