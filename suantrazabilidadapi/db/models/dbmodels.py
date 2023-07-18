import os
from suantrazabilidadapi.core.config import config
from sqlalchemy import Column, create_engine
from sqlalchemy import Integer, Text, Boolean
from alembic.config import Config
from alembic import command
from typing import List
from alembic.util import CommandError
from alembic.script import ScriptDirectory

from ..dblib import Base
from .mixins import Timestamp, create_dataType


class Projects(Timestamp, Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    suanid = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    categoryid = Column(Text, nullable=True)
    status = Column(Text, nullable=False)

def kobo_data_tables(form_id_list: List[str], column_schema_list: List[dict]) -> str:

    """_summary_
    ** column_schema: {column_name: column_type}
    """
    params = config(section="postgresql")

    for i, form_id in enumerate(form_id_list):
        create_dataType(form_id, column_schema_list[i])

    # Perform the Alembic upgrade
    conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"

    alembic_cfg = Config('suantrazabilidadapi/alembic.ini')
    alembic_cfg.set_main_option('script_location', 'suantrazabilidadapi/alembic')
    alembic_cfg.set_main_option('sqlalchemy.url', conn_string)

    engine = create_engine(conn_string)

    try:

        with engine.begin() as connection:
            alembic_cfg.attributes["connection"] = connection
            command.revision(alembic_cfg, autogenerate=True, message="Auto-generated migration")

            script_directory = ScriptDirectory.from_config(alembic_cfg)
            latest_revision = script_directory.get_current_head()
            migration_script_path = script_directory.get_revision(latest_revision).path
            with open(migration_script_path) as file:
                migration_script_contents = file.read()
            
            # Check if the migration script contains only a `pass` statement
            if 'pass' in migration_script_contents:
                msg = f"No changes detected. Skipping migration."
                if os.path.exists(migration_script_path):
                    os.remove(migration_script_path)
            else:
                command.upgrade(alembic_cfg, "head")

                msg = f"Upgrade completed successfully for the following forms: {form_id_list}"
    
    except CommandError as e:
        msg = f'Upgrade failed: {str(e)}'

    return msg

class Principalform(Base):
    __tablename__ = "principalform"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    proyecto = Column(Boolean, nullable=False)
    featureName = Column(Text, nullable=True)
    featureType = Column(Text, nullable=True)
    format = Column(Text, nullable=True)