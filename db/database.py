import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")


DATABASE_URL = f"mysql+pymysql://{user}:{password}@localhost:3306/student_grades?charset=utf8mb4"

# future=True ya viene implícito en SQLAlchemy 2.x
engine = create_engine(
    DATABASE_URL,
    echo=True,          # ver SQL en consola
    pool_pre_ping=True,  # evita conexiones muertas
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager para manejo seguro de sesión:
    - commit automático si va bien
    - rollback si hay excepción
    - cierre garantizado
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()