import os
from typing import Any, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import api_router
from app.core import get_settings
from app.db import Base


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """テスト用アプリケーションインスタンス"""
    app = FastAPI()
    app.include_router(api_router)
    return app


@pytest.fixture(scope="module")
def client(app: FastAPI) -> Generator:
    """テスト用クライアント"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_engine():
    """テスト用データベースエンジン
    インメモリーSQLiteを使用
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """テスト用DBセッション
    テストごとにロールバックされる
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
