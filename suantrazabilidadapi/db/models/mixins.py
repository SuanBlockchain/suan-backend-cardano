from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, BigInteger, Text, Numeric
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.types import TypeDecorator
from ..dblib import Base
import pandas as pd

column_exclusions = [
    "note",
    "begin_group",
    "end_group"
]

@declarative_mixin
class Timestamp:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def create_dataType(form_id: str, column_schema: dict) -> type:

    table_name = f'kobo_data_{form_id}'
    columns = {
        '__tablename__': table_name,
        'id': Column(Integer, primary_key=True),
        'kobo_id': Column(BigInteger, nullable=False)
    }

    for column_name, column_type in column_schema.items():
        columns[column_name] = Column(column_type, nullable=True)
    
    table_class = type(table_name, (Base,), {
        '__tablename__': table_name,
        '__table_args__': {'extend_existing': True},
        **columns
    }
    )

    return table_class

def build_schema(form_template: pd.DataFrame) -> dict:
    column_schema = {}
    column_schema_dict = {}
    for index, row in form_template.iterrows():
        type = row["type"]
        if type not in column_exclusions:
            if type == "text" or "select_one" in type or "select_multiple" in type or type == "file" or type == "image":
                column_schema = {
                    row["name"]: Text
                }
            elif type == "integer":
                column_schema = {
                    row["name"]: Integer
                }
            elif type == "date":
                column_schema = { row["name"]: DateTime}
            elif type == "decimal":
                column_schema = { row["name"]: Numeric}
        
        if column_schema != {}:
            column_schema_dict.update(column_schema)

    return column_schema_dict
