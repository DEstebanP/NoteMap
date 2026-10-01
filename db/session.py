from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base

DB_PATH = Path(__file__).resolve().parent.parent / 'instance' / 'notes.sqlite'
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def init_db():
    Base.metadata.create_all(engine)
