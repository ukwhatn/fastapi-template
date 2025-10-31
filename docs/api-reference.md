# API Reference

本テンプレートの共通コンポーネント・ヘルパー関数リファレンス。

## データベース基底クラス

### Base

**場所**: `app/infrastructure/database/models/base.py`

SQLAlchemy DeclarativeBase。全モデルの基底クラス。

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass
```

### TimeStampMixin

**場所**: `app/infrastructure/database/models/base.py`

タイムスタンプ自動管理Mixin。

```python
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class TimeStampMixin:
    """
    タイムスタンプMixin

    Attributes:
        created_at: 作成日時（自動設定）
        updated_at: 更新日時（自動更新）
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### BaseModel

**場所**: `app/infrastructure/database/models/base.py`

Base + TimeStampMixin + id。全モデルの推奨基底クラス。

```python
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

class BaseModel(Base, TimeStampMixin):
    """
    ベースモデル
    全てのモデルで継承して使用

    Attributes:
        id: 主キー（自動インクリメント）
        created_at: 作成日時（TimeStampMixinから継承）
        updated_at: 更新日時（TimeStampMixinから継承）
    """
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
```

**使用例**:
```python
from app.infrastructure.database.models.base import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class User(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    # id, created_at, updated_at は自動的に追加される
```

## セッション管理

### SessionSchema

**場所**: `app/utils/schemas.py`

セッションデータを保持するPydantic BaseModel。

```python
from pydantic import BaseModel, ConfigDict
from typing import Any

class SessionSchema(BaseModel):
    """
    セッションデータスキーマ

    Attributes:
        data: セッションデータ（辞書形式）
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: dict[str, Any] = {}
```

**使用例**:
```python
from app.utils.schemas import SessionSchema

session = SessionSchema(data={"user_id": 123, "role": "admin"})
user_id = session.data.get("user_id")
```

### セッションヘルパー関数

**場所**: `app/utils/session_helper.py`

#### get_client_ip

```python
def get_client_ip(request: Request) -> Optional[str]:
    """
    クライアントIPアドレスを取得

    優先順位: CF-Connecting-IP > X-Forwarded-For > client.host

    Args:
        request: FastAPI Request

    Returns:
        クライアントIPアドレス
    """
```

#### get_user_agent

```python
def get_user_agent(request: Request) -> Optional[str]:
    """
    User-Agentヘッダーを取得

    Args:
        request: FastAPI Request

    Returns:
        User-Agentヘッダー
    """
```

#### create_session

```python
def create_session(
    db: DBSession,
    response: Response,
    request: Request,
    data: dict[str, Any],
) -> tuple[str, str]:
    """
    新しいセッションを作成してCookieに設定

    Args:
        db: DBセッション
        response: FastAPI Response
        request: FastAPI Request
        data: セッションデータ

    Returns:
        (session_id, csrf_token) のタプル
    """
```

#### get_session_data

```python
def get_session_data(
    db: DBSession,
    request: Request,
    verify_csrf: bool = False,
    csrf_token: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    セッションデータを取得

    Args:
        db: DBセッション
        request: FastAPI Request
        verify_csrf: CSRFトークンを検証するか
        csrf_token: CSRFトークン（verify_csrf=Trueの場合）

    Returns:
        セッションデータ、存在しない場合はNone
    """
```

#### update_session_data

```python
def update_session_data(
    db: DBSession,
    request: Request,
    data: dict[str, Any],
) -> bool:
    """
    セッションデータを更新

    Args:
        db: DBセッション
        request: FastAPI Request
        data: 新しいセッションデータ

    Returns:
        更新成功時True
    """
```

#### delete_session

```python
def delete_session(
    db: DBSession,
    request: Request,
    response: Response,
) -> bool:
    """
    セッションを削除してCookieをクリア

    Args:
        db: DBセッション
        request: FastAPI Request
        response: FastAPI Response

    Returns:
        削除成功時True
    """
```

#### regenerate_session_id

```python
def regenerate_session_id(
    db: DBSession,
    request: Request,
    response: Response,
) -> Optional[tuple[str, str]]:
    """
    セッションIDを再生成（ログイン時などに使用）

    Args:
        db: DBセッション
        request: FastAPI Request
        response: FastAPI Response

    Returns:
        (新しいsession_id, 新しいcsrf_token) のタプル、失敗時はNone
    """
```

#### get_csrf_token

```python
def get_csrf_token(db: DBSession, request: Request) -> Optional[str]:
    """
    CSRFトークンを取得

    Args:
        db: DBセッション
        request: FastAPI Request

    Returns:
        CSRFトークン、セッションが存在しない場合はNone
    """
```

## テンプレートヘルパー

### get_templates

**場所**: `app/utils/templates.py`

```python
from typing import Optional
from fastapi import Request
from fastapi.templating import Jinja2Templates

def get_templates(request: Request) -> Optional[Jinja2Templates]:
    """
    リクエストからJinja2Templatesインスタンスを取得

    Args:
        request: FastAPIのRequestオブジェクト

    Returns:
        Jinja2Templatesインスタンス、または無効な場合はNone
    """
```

**使用例**:
```python
from app.utils.templates import get_templates

@router.get("/")
async def index(request: Request):
    templates = get_templates(request)
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return {"message": "Templates not available"}
```

## 依存性注入

### get_db

**場所**: `app/infrastructure/database/connection.py`

```python
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    """
    DBセッション取得

    Yields:
        Session: SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**使用例**:
```python
from fastapi import Depends
from sqlalchemy.orm import Session

@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

### get_session

**場所**: `app/presentation/api/deps.py`

```python
from fastapi import Request
from app.utils.schemas import SessionSchema

def get_session(request: Request) -> SessionSchema:
    """
    セッションデータを取得するdependency

    Args:
        request: FastAPI Request

    Returns:
        SessionSchema: セッションデータ
    """
```

**使用例**:
```python
from fastapi import Depends
from app.utils.schemas import SessionSchema

@router.get("/profile")
async def get_profile(session: SessionSchema = Depends(get_session)):
    user_id = session.data.get("user_id")
    if not user_id:
        raise UnauthorizedError("Not logged in")
    # ...
```

### get_db_with_session

**場所**: `app/presentation/api/deps.py`

```python
from dataclasses import dataclass
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.schemas import SessionSchema

@dataclass
class DBWithSession:
    db: Session
    session: SessionSchema

def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[DBWithSession, None, None]:
    """
    DBとセッションの両方を取得するdependency

    Yields:
        DBWithSession: DB + セッション
    """
    yield DBWithSession(db=db, session=session)
```

**使用例**:
```python
from fastapi import Depends
from app.presentation.api.deps import DBWithSession, get_db_with_session

@router.get("/protected")
async def protected_endpoint(deps: DBWithSession = Depends(get_db_with_session)):
    user_id = deps.session.data.get("user_id")
    if not user_id:
        raise UnauthorizedError("Not logged in")

    user = deps.db.query(User).filter_by(id=user_id).first()
    return user
```

### get_api_key

**場所**: `app/presentation/api/deps.py`

```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="Authorization", scheme_name="Bearer", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    APIキー認証のdependency

    Authorization: Bearer your-api-key-here

    Args:
        api_key_header: Authorizationヘッダー

    Returns:
        APIキー

    Raises:
        HTTPException: 認証失敗時
    """
```

**使用例**:
```python
from fastapi import Depends

@router.get("/api-protected")
async def api_protected_endpoint(api_key: str = Depends(get_api_key)):
    return {"message": "API authenticated", "api_key": api_key}
```

## ロギング

### get_logger

**場所**: `app/core/logging.py`

```python
import logging

def get_logger(name: str) -> logging.Logger:
    """
    ロガー取得

    Args:
        name: ロガー名（通常は__name__を使用）

    Returns:
        logging.Logger: ロガーインスタンス
    """
```

**使用例**:
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

## 設定管理

### get_settings

**場所**: `app/core/config.py`

```python
from functools import lru_cache
from app.core.config import Settings

@lru_cache
def get_settings() -> Settings:
    """
    設定を取得（シングルトン）

    Returns:
        Settings: 設定インスタンス
    """
```

**使用例**:
```python
from app.core.config import get_settings

settings = get_settings()

database_url = settings.database_uri
is_production = settings.is_production
session_expire = settings.SESSION_EXPIRE
```

## セキュリティ

### SessionEncryption

**場所**: `app/infrastructure/security/encryption.py`

```python
class SessionEncryption:
    """
    セッションデータの暗号化/復号化

    Fernet (対称暗号化) を使用
    """
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Args:
            encryption_key: 暗号化キー（Noneの場合は設定から取得）
        """

    def encrypt(self, data: dict[str, Any]) -> str:
        """セッションデータを暗号化"""

    def decrypt(self, encrypted_data: str) -> dict[str, Any]:
        """暗号化されたセッションデータを復号化"""
```

**使用例**:
```python
from app.infrastructure.security.encryption import SessionEncryption

encryption = SessionEncryption()

# 暗号化
encrypted = encryption.encrypt({"user_id": 123})

# 復号化
data = encryption.decrypt(encrypted)
```

### generate_csrf_token

**場所**: `app/infrastructure/security/encryption.py`

```python
def generate_csrf_token() -> str:
    """
    CSRFトークンを生成

    Returns:
        ランダムな64文字のHEX文字列
    """
```

### generate_session_id

**場所**: `app/infrastructure/security/encryption.py`

```python
def generate_session_id() -> str:
    """
    セッションIDを生成

    Returns:
        ランダムな64文字のHEX文字列
    """
```

### generate_fingerprint

**場所**: `app/infrastructure/security/encryption.py`

```python
def generate_fingerprint(user_agent: Optional[str], client_ip: Optional[str]) -> str:
    """
    セッションフィンガープリントを生成

    User-AgentとクライアントIPのSHA256ハッシュを生成

    Args:
        user_agent: User-Agentヘッダー
        client_ip: クライアントIPアドレス

    Returns:
        SHA256ハッシュ（64文字のHEX文字列）
    """
```

### verify_fingerprint

**場所**: `app/infrastructure/security/encryption.py`

```python
def verify_fingerprint(
    stored_fingerprint: str,
    user_agent: Optional[str],
    client_ip: Optional[str]
) -> bool:
    """
    セッションフィンガープリントを検証

    Args:
        stored_fingerprint: 保存されているフィンガープリント
        user_agent: 現在のUser-Agentヘッダー
        client_ip: 現在のクライアントIPアドレス

    Returns:
        フィンガープリントが一致する場合True
    """
```

## 参考資料

- [Architecture](architecture.md) - Clean Architecture実装詳細
- [Error Handling](features/error-handling.md) - エラーハンドリング
- [Session Management](features/session-management.md) - セッション管理
- [Database Backup](features/database-backup.md) - バックアップシステム
- [Batch System](features/batch-system.md) - バッチ処理
