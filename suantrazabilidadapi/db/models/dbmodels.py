from sqlalchemy import BigInteger, Boolean, Column, Enum
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
from alembic.config import Config
from alembic import command

from datetime import datetime

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

    suan = relationship("Kobo_data", back_populates="suan")



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

    koboform = relationship("Kobo_data", back_populates="kobo_forms")

class Kobo_data(Base):
    __tablename__ = "kobo_data"

    id = Column(Integer, primary_key=True)
    id_form = Column(Integer, ForeignKey('kobo_forms.id'), nullable=True)
    id_suan = Column(Integer, ForeignKey('projects.id'), nullable=False)
    username = Column(Text, nullable=True)
    phonenumber = Column(Text, nullable=True)
    kobo_id = Column(BigInteger, nullable=True)
    submission_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    text = Column(Text, nullable=True)
    geopoint_map = Column(Text, nullable=True)
    annotate = Column(Text, nullable=True)
    text_001 = Column(Text, nullable=True)
    geotrace = Column(Text, nullable=True)
    text_002 = Column(Text, nullable=True)
    geoshape = Column(Text, nullable=True)
    geopoint_hide = Column(Text, nullable=True)
    audit = Column(Text, nullable=True)

    suan = relationship("Projects", back_populates="suan")
    kobo_forms = relationship("Kobo_forms", back_populates="koboform")


def kobo_data_tables(form_id: str, **column_schema):

    """_summary_
    ** column_schema: {column_name: column_type}
    """
    column_definitions = []
    table_name = f'kobo_data_{form_id}'
    for column_name, column_type in column_schema.items():
        column = Column(column_type, nullable=True)
        column_definitions.append((column_name, column))
    
    columns = {
        '__tablename__': table_name,
        'id': Column(Integer, primary_key=True),
    }
    columns.update(column_definitions)

    
    type('Data', (Base,), columns)

    # Perform the Alembic upgrade
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option('script_location', 'your_migration_directory')
    alembic_cfg.set_main_option('sqlalchemy.url', 'your_database_connection_string')

    # Run the Alembic upgrade command programmatically
    with alembic_cfg.connect() as connection:
        context = alembic_cfg.configure(connection=connection)
        command.upgrade(context, 'head')
    