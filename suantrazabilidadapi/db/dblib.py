from configparser import ConfigParser
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from suantrazabilidadapi.core.config import config

""" Connect to the PostgreSQL database server using SQLAlchemy method """
# read connection parameters
params = config(section="postgresql")

print(params)

# connect to the PostgreSQL server
print("Connecting to the PostgreSQL database...")
conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"
print(conn_string)
engine = create_engine(conn_string, connect_args={}, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()
connection = engine.connect()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
