
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import config


""" Connect to the PostgreSQL database server using SQLAlchemy method """
# read connection parameters
params = config(section="postgresql")

# connect to the PostgreSQL server
print("Connecting to the PostgreSQL database...")
conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"
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
