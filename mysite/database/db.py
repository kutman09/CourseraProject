from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_PATH = Path(__file__).resolve().parents[2] / 'database.db'
engine = create_engine(f'sqlite:///{DATABASE_PATH.as_posix()}', connect_args={'check_same_thread': False})

@event.listens_for(engine, 'connect')
def enable_foreign_keys(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db
