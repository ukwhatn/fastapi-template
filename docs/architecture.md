# Architecture

本テンプレートのアーキテクチャ設計と実装詳細。

## Clean Architecture

### 概要

4層構造のClean Architectureを採用し、ビジネスロジックとフレームワーク・外部依存の分離を実現。

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │  ← FastAPI、ルーター、スキーマ
│  (app/presentation/)                    │
└────────────┬────────────────────────────┘
             │ depends on
┌────────────▼────────────────────────────┐
│       Infrastructure Layer              │  ← DB、リポジトリ実装、外部サービス
│  (app/infrastructure/)                  │
└────────────┬────────────────────────────┘
             │ implements
┌────────────▼────────────────────────────┐
│        Application Layer                │  ← ユースケース、インターフェース
│  (app/application/)                     │
└────────────┬────────────────────────────┘
             │ depends on
┌────────────▼────────────────────────────┐
│          Domain Layer                   │  ← ビジネスロジック、例外
│  (app/domain/)                          │     NO DEPENDENCIES
└─────────────────────────────────────────┘
```

### レイヤー詳細

#### Domain Layer (`app/domain/`)

**責務**：
- ビジネスルールの定義
- ドメイン例外の定義
- エンティティ、値オブジェクト

**依存関係**：
- なし（外部ライブラリにも依存しない）

**ディレクトリ構造**：
```
app/domain/
├── exceptions/
│   └── base.py          # DomainError、NotFoundError等
├── entities/            # ドメインエンティティ
└── value_objects/       # 値オブジェクト
```

**実装例**：
```python
# app/domain/exceptions/base.py
class DomainError(Exception):
    def __init__(self, message: str, code: str, details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found", details: Optional[dict] = None):
        super().__init__(message=message, code="not_found", details=details)
```

**原則**：
- フレームワーク非依存
- データベース非依存
- UI非依存
- 純粋なPythonコード

#### Application Layer (`app/application/`)

**責務**：
- ユースケースの定義
- リポジトリインターフェースの定義
- DTO（Data Transfer Object）
- ビジネスロジックのオーケストレーション

**依存関係**：
- Domain層のみに依存

**ディレクトリ構造**：
```
app/application/
├── use_cases/           # ユースケース実装
├── interfaces/          # リポジトリインターフェース
├── dtos/                # データ転送オブジェクト
└── services/            # アプリケーションサービス
```

**実装例**（インターフェース）：
```python
# app/application/interfaces/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional

class IUserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass
```

**原則**：
- フレームワーク非依存（FastAPI不使用）
- データベース実装の詳細を知らない
- インターフェースのみ定義、実装はInfrastructure層

#### Infrastructure Layer (`app/infrastructure/`)

**責務**：
- データベースアクセス（SQLAlchemy）
- リポジトリの実装
- 外部サービス連携
- セキュリティ機能（暗号化等）
- バッチ処理

**依存関係**：
- Application層のインターフェースを実装
- Domain層の例外を使用

**ディレクトリ構造**：
```
app/infrastructure/
├── database/
│   ├── models/          # SQLAlchemyモデル
│   ├── connection.py    # DB接続管理
│   ├── migration.py     # マイグレーション実行
│   ├── alembic/         # Alembic設定・バージョン
│   └── backup/          # バックアップシステム
├── repositories/        # リポジトリ実装
├── security/            # 暗号化、認証
├── batch/               # バッチ処理
└── external/            # 外部API連携
```

**実装例**（リポジトリ）：
```python
# app/infrastructure/repositories/user_repository.py
from app.application.interfaces.user_repository import IUserRepository
from app.domain.exceptions.base import NotFoundError

class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    async def find_by_id(self, user_id: int) -> Optional[User]:
        user = self.db.query(UserModel).filter_by(id=user_id).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user
```

**原則**：
- Application層のインターフェースを実装
- 具体的な技術選択（SQLAlchemy、PostgreSQL等）
- Domain層の例外を使用

#### Presentation Layer (`app/presentation/`)

**責務**：
- HTTPリクエスト・レスポンス処理
- ルーティング
- バリデーション（Pydantic）
- 認証・認可
- エラーハンドリング（HTTP変換）

**依存関係**：
- すべての層に依存可能
- Infrastructure層を通じてApplication層を利用

**ディレクトリ構造**：
```
app/presentation/
├── api/
│   ├── v1/              # API v1エンドポイント
│   ├── system/          # システムエンドポイント（health check等）
│   └── deps.py          # 依存性注入
├── schemas/             # Pydanticスキーマ
├── middleware/          # ミドルウェア
└── exceptions/          # HTTPエラークラス
```

**実装例**（ルーター）：
```python
# app/presentation/api/v1/users.py
from fastapi import APIRouter, Depends
from app.presentation.schemas.user import UserResponse
from app.infrastructure.repositories.user_repository import UserRepository
from app.domain.exceptions.base import NotFoundError

router = APIRouter()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    return UserResponse.from_orm(user)
```

**原則**：
- FastAPI特有のコード
- HTTP層の詳細を他層に漏らさない
- Domain例外をHTTPエラーに変換

### 依存性の方向

**必須ルール**：
```
Domain ← Application ← Infrastructure
  ↑                       ↓
  └──────── Presentation ─┘
```

- **Domain**: 誰にも依存しない
- **Application**: Domainのみに依存
- **Infrastructure**: ApplicationとDomainに依存
- **Presentation**: すべてに依存可能

**違反例**：
```python
# ❌ BAD: Domain層でFastAPIに依存
from fastapi import HTTPException  # NG

class DomainError(HTTPException):  # NG
    pass
```

```python
# ✅ GOOD: Domain層は純粋なPython例外
class DomainError(Exception):
    pass
```

## 依存性注入（DI）

### FastAPI Dependsパターン

**基本的な依存性**：

```python
# app/presentation/api/deps.py
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    """DBセッション取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session(request: Request) -> SessionSchema:
    """セッションデータ取得"""
    return SessionSchema(data=request.state.session or {})
```

**複合的な依存性**：

```python
@dataclass
class DBWithSession:
    db: Session
    session: SessionSchema

def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[DBWithSession, None, None]:
    """DB + セッションの両方を取得"""
    yield DBWithSession(db=db, session=session)
```

**使用例**：

```python
@router.get("/profile")
async def get_profile(deps: DBWithSession = Depends(get_db_with_session)):
    db = deps.db
    session = deps.session
    # ...
```

### リポジトリの注入

**インターフェースベース**：

```python
# Application層
class IUserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: int) -> User:
        pass

# Infrastructure層
class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    async def find_by_id(self, user_id: int) -> User:
        # 実装
        pass

# Presentation層
def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    return UserRepository(db)

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    repo: IUserRepository = Depends(get_user_repository)
):
    user = await repo.find_by_id(user_id)
    return user
```

## エラーハンドリング

### フロー

```
1. Domain層で例外発生
   ↓
2. main.pyの例外ハンドラーがキャッチ
   ↓
3. domain_error_to_api_error()で変換
   ↓
4. ErrorResponse（JSON）を返却
```

**実装**：

```python
# main.py
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> Response:
    api_error = domain_error_to_api_error(exc)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )
```

詳細は [Error Handling](features/error-handling.md) を参照。

## データベース設計

### モデル継承

**基底クラス**：

```python
# app/infrastructure/database/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass

class TimeStampMixin:
    """タイムスタンプ自動管理"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class BaseModel(Base, TimeStampMixin):
    """全モデルの基底クラス"""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
```

**使用例**：

```python
class User(BaseModel):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    # id, created_at, updated_at は自動的に継承される
```

### マイグレーション

**自動実行**：

アプリケーション起動時に自動的にマイグレーションを実行。

```python
# app/main.py
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.has_database:
        from .infrastructure.database.migration import run_migrations
        run_migrations(logger_key="uvicorn")
    # ...
```

**手動実行**：

```bash
make db:migrate                             # マイグレーション適用
make db:revision:create NAME="description"  # マイグレーション作成
make db:current                             # 現在のリビジョン
make db:history                             # 履歴表示
```

## ミドルウェア

### セッションミドルウェア

**実装** (`app/main.py`):

```python
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    if settings.has_database:
        db = next(get_db())
        try:
            session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if session_id:
                service = SessionService(db)
                user_agent = request.headers.get("User-Agent")
                client_ip = get_client_ip(request)  # CF-Connecting-IP > X-Forwarded-For > client.host

                session_data = service.get_session(session_id, user_agent, client_ip)
                request.state.session = session_data or {}
                request.state.session_id = session_id
            else:
                request.state.session = {}

            response = await call_next(request)
            return response
        finally:
            db.close()
    else:
        request.state.session = None
        return await call_next(request)
```

**特徴**：
- 自動保存はしない（パフォーマンス考慮）
- 各エンドポイントで明示的に保存
- フィンガープリント検証を実施

### エラーハンドリングミドルウェア

**実装**:

```python
@app.middleware("http")
async def error_response(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Unhandled exception: {str(e)}", exc_info=e)

        error = ErrorResponse(
            code="internal_server_error",
            message="Internal server error occurred",
        )
        return Response(
            content=json.dumps(jsonable_encoder(error)),
            status_code=500,
            media_type="application/json",
        )
```

### セキュリティヘッダーミドルウェア

**実装** (`app/presentation/middleware/security_headers.py`):

セキュリティヘッダーを自動付与。

## ライフサイクル管理

### アプリケーション起動時

```python
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. マイグレーション実行
    if settings.has_database:
        from .infrastructure.database.migration import run_migrations
        run_migrations(logger_key="uvicorn")

    # 2. バッチスケジューラー起動
    from .infrastructure.batch.scheduler import create_scheduler, start_scheduler
    from .infrastructure.batch import tasks  # タスク自動登録

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    start_scheduler(scheduler)

    # 3. 静的ファイル・テンプレートマウント
    if has_content(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    if has_content(TEMPLATES_DIR):
        app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    yield

    # 4. シャットダウン処理
    stop_scheduler(scheduler)
```

### 統合サービス

**Sentry**:
```python
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    )
```

**New Relic** (本番環境のみ):
```python
if settings.is_production and settings.NEW_RELIC_LICENSE_KEY:
    import newrelic.agent
    newrelic.agent.initialize(config_file="/etc/newrelic.ini", environment=settings.ENV_MODE)
```

## ベストプラクティス

### 1. レイヤー分離の徹底

```python
# ❌ BAD: Presentation層でビジネスロジック
@router.post("/users")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # ビジネスロジックをルーター内に直接記述
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    # ...

# ✅ GOOD: Application層にユースケースを定義
class CreateUserUseCase:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def execute(self, user_data: UserCreateDTO) -> User:
        # ビジネスロジック
        if len(user_data.password) < 8:
            raise ValidationError("Password too short")
        # ...

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case)
):
    return await use_case.execute(user_data)
```

### 2. Domain例外の使用

```python
# ❌ BAD: HTTPExceptionを直接raise
from fastapi import HTTPException

def find_user(user_id: int):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

# ✅ GOOD: Domain例外を使用
from app.domain.exceptions.base import NotFoundError

def find_user(user_id: int):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise NotFoundError(f"User {user_id} not found", details={"user_id": user_id})
    # main.pyの例外ハンドラーが自動的にHTTP 404に変換
```

### 3. 依存性注入の活用

```python
# ❌ BAD: リポジトリを直接インスタンス化
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)  # ハードコーディング
    user = await repo.find_by_id(user_id)
    return user

# ✅ GOOD: 依存性注入でリポジトリを取得
def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    return UserRepository(db)

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    repo: IUserRepository = Depends(get_user_repository)
):
    user = await repo.find_by_id(user_id)
    return user
```

### 4. 型ヒントの徹底

```python
# ❌ BAD: 型ヒントなし
def get_user(user_id):
    return db.query(User).filter_by(id=user_id).first()

# ✅ GOOD: 厳格な型ヒント
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    return db.query(User).filter_by(id=user_id).first()
```

## 参考資料

- [Error Handling](features/error-handling.md) - エラーハンドリング詳細
- [Session Management](features/session-management.md) - セッション管理詳細
- [API Reference](api-reference.md) - 共通コンポーネントリファレンス
