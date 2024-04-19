import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)


# get envs
POSTGRES_USER = get_env("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = get_env("POSTGRES_PASSWORD", "password")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/main"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
