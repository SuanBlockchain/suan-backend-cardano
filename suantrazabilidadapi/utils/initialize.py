
from dataclasses import dataclass, field
import os

from suantrazabilidadapi.db.dblib import SessionLocal
from suantrazabilidadapi.db.models import dbmodels
from suantrazabilidadapi.core.config import config

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.util import CommandError
import os
from sqlalchemy.engine.reflection import Inspector

import pandas as pd

@dataclass()
class DbService:
    session = SessionLocal()
    Base = declarative_base()
    params = config(section="postgresql")

    # Perform the Alembic upgrade
    conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"

    alembic_cfg = Config("suantrazabilidadapi/alembic.ini")
    alembic_cfg.set_main_option("script_location", "suantrazabilidadapi/alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", conn_string)

    tables: list = field(default_factory=list) # Declare empty variable for list of tables

    def __post_init__(self):
        self.engine = create_engine(self.conn_string)
        self.inspector = Inspector.from_engine(self.engine)
        self.excel_file = pd.ExcelFile(os.getcwd() + '/suantrazabilidadapi/utils/data/IntegracionKobo.xlsx')

        for sheet_name in self.excel_file.sheet_names:
            if not self.inspector.has_table(sheet_name):
                self.tables.append(sheet_name)

    def _addFirstData(self) -> list[str]:
        # Read the Excel file into a pandas ExcelFile object

        # Iterate over each sheet in the Excel file
        msgs = []

        for sheet_name in self.excel_file.sheet_names:

            class_name = sheet_name.title()
            # Read the current sheet into a pandas DataFrame
            df = self.excel_file.parse(sheet_name)
            data_list = df.to_dict(orient='records')
            model_class = getattr(dbmodels, class_name)

            if sheet_name not in self.tables:
                has_data = self.session.query(model_class).count() > 0

            if sheet_name in self.tables or not has_data:
                instances = []
                for item in data_list:
                    instance = model_class(**item)
                    instances.append(instance)
                self.session.add_all(instances)
                self.session.flush()
                msg = f'Data updated succesfully in postgresQL for table: {sheet_name}'
                try:
                    self.session.commit()
                except SQLAlchemyError as e:
                    self.session.rollback()
                    msg = f'An error occurred during the database commit:", {str(e)} for table: {class_name}'
                    print(msg)
                    msgs.append(msg)

                sequence_name = f'{sheet_name}_id_seq'
                result = self.session.execute(text(f"SELECT MAX(id) FROM {sheet_name}"))
                max_id = result.scalar()
                if max_id is not None:
                    self.session.execute(text(f"SELECT setval('{sequence_name}', {max_id}, true)"))
                self.session.close()
                
            else:

                msg = f'Data already exists in postgresQl for table: {sheet_name}'
            
            msgs.append(msg)

        
            
        
        

        return msgs


