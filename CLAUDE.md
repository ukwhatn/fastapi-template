# CLAUDE.md - AI Implementation Guide

このテンプレートからアプリケーションを作成する際のAI向け実装ガイド。

## プロジェクト概要

FastAPIプロダクションテンプレート。Clean Architecture（4層）、RDBベース暗号化セッション、Vite+Reactフロントエンド統合、包括的Docker展開を提供。

**技術スタック**:
- **バックエンド**: FastAPI 0.120.0+, Python 3.13+, SQLAlchemy 2.0+, PostgreSQL
- **フロントエンド**: Vite 6.x, React 19.x, TypeScript 5.x, React Router 7.x, TanStack Query 5.x, Tailwind CSS 4.x
- **ツール**: uv, pnpm, Ruff, mypy strict, pytest
- **インフラ**: Docker Compose (multi-stage build, multi-profile), APScheduler, Sentry, New Relic

**主要機能**:
- Clean Architecture 4層構造
- Vite+Reactフロントエンド統合（SPA fallback対応）
- RDBベースセッション管理（Fernet暗号化、CSRF保護、フィンガープリント検証）
- psycopg2ベースバックアップシステム（S3連携）
- APSchedulerバッチシステム
- 自動マイグレーション（起動時実行）

## コマンドリファレンス

**開発**:
```bash
make dev:setup              # 依存関係インストール
make frontend:install       # フロントエンド依存関係インストール
make local:up               # DBサービス起動
make local:serve            # バックエンド + フロントエンド並列起動（ホットリロード）
make local:serve:backend    # バックエンドのみ起動
make local:serve:frontend   # フロントエンドのみ起動
make lint                   # バックエンドリント
make type-check             # バックエンド型チェック
make test                   # バックエンドテスト
```

**フロントエンド**:
```bash
make frontend:build         # 本番ビルド
make frontend:lint          # ESLint実行
make frontend:lint:fix      # ESLint修正
make frontend:type-check    # TypeScriptチェック
```

**データベース**:
```bash
make db:revision:create NAME="description"      # マイグレーション作成
make db:migrate                                 # マイグレーション適用（手動）
make db:backup:oneshot                          # バックアップ作成
make db:backup:restore FILE="xxx.backup.gz"     # リストア
```

**IMPORTANT**: `make`コマンドが利用可能な場合は必ず使用すること。

## Clean Architecture

### 4層構造

```
Presentation → Infrastructure → Application → Domain
```

**依存関係ルール**（厳守）:
- Domain: 誰にも依存しない
- Application: Domainのみに依存
- Infrastructure: Application/Domainに依存
- Presentation: 全レイヤーに依存可能

### レイヤー配置

| レイヤー | パス | 責務 |
|---------|------|------|
| Domain | `app/domain/` | ビジネスロジック、例外定義 |
| Application | `app/application/` | ユースケース、インターフェース |
| Infrastructure | `app/infrastructure/` | DB、リポジトリ実装 |
| Presentation | `app/presentation/` | ルーター、スキーマ、ミドルウェア |

詳細: [docs/architecture.md](docs/architecture.md)

## Domain例外（必須知識）

**場所**: `app/domain/exceptions/base.py`

### 利用可能な例外クラス

| クラス | HTTPステータス | code | 用途 |
|-------|---------------|------|------|
| `DomainError` | 500 | - | 基底クラス |
| `NotFoundError` | 404 | `not_found` | リソース不存在 |
| `BadRequestError` | 400 | `bad_request` | 不正リクエスト |
| `UnauthorizedError` | 401 | `unauthorized` | 認証エラー |
| `ForbiddenError` | 403 | `forbidden` | 権限エラー |
| `ValidationError` | 400 | `validation_error` | バリデーションエラー |

### DomainError構造

```python
class DomainError(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details
```

### 使用例

```python
from app.domain.exceptions.base import NotFoundError, UnauthorizedError, ValidationError

# リソース不存在
if not user:
    raise NotFoundError(f"User {user_id} not found", details={"user_id": user_id})

# 認証エラー
if not session.data.get("user_id"):
    raise UnauthorizedError("Authentication required")

# バリデーションエラー（複数）
errors = []
if len(password) < 8:
    errors.append({"field": "password", "error": "Too short"})
if "@" not in email:
    errors.append({"field": "email", "error": "Invalid format"})
if errors:
    raise ValidationError("Validation failed", details=errors)
```

**IMPORTANT**: HTTPExceptionを直接raiseせず、必ずDomain例外を使用すること。main.pyの例外ハンドラーが自動的にHTTPレスポンスに変換する。

詳細: [docs/features/error-handling.md](docs/features/error-handling.md)

## セッション管理（RDBベース）

### 特徴

- **RDBベース**（RedisではなくPostgreSQL）
- **Fernet暗号化**
- **CSRF保護**
- **フィンガープリント検証**（User-Agent + IP）
- **セッション固定攻撃対策**（セッションID再生成）

### 実装パターン

#### ログイン

```python
from app.utils.session_helper import create_session
from app.domain.exceptions.base import UnauthorizedError

@router.post("/login")
async def login(
    credentials: LoginCredentials,
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    # 認証処理
    user = authenticate(credentials)
    if not user:
        raise UnauthorizedError("Invalid credentials")

    # セッション作成（Cookieに自動設定）
    session_id, csrf_token = create_session(
        db, response, request,
        data={"user_id": user.id, "role": user.role}
    )

    return {"csrf_token": csrf_token}
```

#### 認証が必要なエンドポイント

```python
from app.presentation.api.deps import DBWithSession, get_db_with_session

@router.get("/profile")
async def get_profile(deps: DBWithSession = Depends(get_db_with_session)):
    user_id = deps.session.data.get("user_id")
    if not user_id:
        raise UnauthorizedError("Not logged in")

    user = deps.db.query(User).filter_by(id=user_id).first()
    return user
```

#### ログアウト

```python
from app.utils.session_helper import delete_session

@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    delete_session(db, request, response)
    return {"message": "Logged out"}
```

#### セッションID再生成（ログイン成功時推奨）

```python
from app.utils.session_helper import regenerate_session_id

@router.post("/login")
async def login(...):
    user = authenticate(credentials)
    regenerate_session_id(db, request, response)
    # ...
```

詳細: [docs/features/session-management.md](docs/features/session-management.md)

## データベース

### 基底クラス（必須使用）

```python
from app.infrastructure/database/models/base import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class YourModel(BaseModel):
    __tablename__ = "your_table"

    name: Mapped[str] = mapped_column(String(100))
    # id, created_at, updated_at は自動的に追加される
```

**BaseModel提供項目**:
- `id: int` (primary key, autoincrement)
- `created_at: datetime` (auto-set)
- `updated_at: datetime` (auto-update)

### マイグレーション

**自動実行**: アプリケーション起動時に自動的に適用される。

**作成手順**:
```bash
# 1. モデルを作成
# app/infrastructure/database/models/your_model.py

# 2. models/__init__.pyにインポート追加
from .your_model import YourModel

# 3. alembic/env.pyにインポート追加（autogenerate検出用）
from app.infrastructure.database.models import YourModel  # noqa: F401

# 4. マイグレーション作成
make db:revision:create NAME="add_your_table"

# 5. マイグレーションファイル確認・編集
# app/infrastructure/database/alembic/versions/xxx_add_your_table.py

# 6. アプリケーション起動時に自動適用
# または手動実行: make db:migrate
```

### バックアップ

```bash
# バックアップ作成
make db:backup:oneshot

# リストア前に差分確認（必須）
make db:backup:diff FILE="backup_20251101_123456.backup.gz"

# リストア
make db:backup:restore FILE="backup_20251101_123456.backup.gz"
```

詳細: [docs/features/database-backup.md](docs/features/database-backup.md)

## バッチシステム

### カスタムタスク作成

```python
# app/infrastructure/batch/tasks/my_task.py
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.batch.registry import TaskRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

class MyCustomTask(BaseTask):
    """カスタムタスクの説明"""
    name = "my_custom_task"
    description = "カスタムタスク"
    schedule = "0 3 * * *"  # 毎日午前3時

    def run(self) -> None:
        logger.info(f"Starting {self.name}")
        # タスクのロジック
        logger.info(f"Completed {self.name}")

# 自動登録
TaskRegistry.register(MyCustomTask)
```

**配置**: `app/infrastructure/batch/tasks/` に配置するだけで自動登録される。

詳細: [docs/features/batch-system.md](docs/features/batch-system.md)

## フロントエンド統合

### アーキテクチャ

**開発環境**:
- Viteがポート5173でフロントエンド開発サーバーを起動
- Vite proxyが`/api/*`リクエストをFastAPI（ポート8000）に転送
- ホットリロード対応

**本番環境**:
- Dockerマルチステージビルドでフロントエンドをビルド（`frontend/dist`）
- FastAPIが静的ファイルとしてフロントエンドを配信
- `SPAStaticFiles`クラスでReact Routerのhistory mode対応（404 → index.html）
- `/api/*`はFastAPIルーター、`/*`はフロントエンドSPA

### ディレクトリ構造

```
frontend/
├── src/
│   ├── pages/           # ページコンポーネント
│   ├── App.tsx          # ルーター設定（React Router）
│   └── main.tsx         # エントリーポイント
├── dist/                # ビルド成果物（本番）
├── package.json
├── pnpm-lock.yaml
├── vite.config.ts       # Vite設定
└── tsconfig.json
```

### Vite設定（proxy）

```typescript
// frontend/vite.config.ts
export default defineConfig({
  plugins: [
    tailwindcss(),  // Tailwind CSS v4
    react(),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### SPAStaticFiles実装

```python
# app/main.py
class SPAStaticFiles(StaticFiles):
    """React Routerのhistory mode対応"""
    async def get_response(self, path: str, scope: dict[str, Any]) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise ex

# lifespanでマウント（APIルーターより後）
if FRONTEND_DIST_DIR.exists() and FRONTEND_DIST_DIR.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
```

### APIクライアント実装例（フロントエンド）

```typescript
// frontend/src/api/client.ts
import { useQuery } from '@tanstack/react-query'

// 型安全なAPIクライアント
async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }
  return response.json()
}

// React Query フック
export function useHealthCheck() {
  return useQuery({
    queryKey: ['healthcheck'],
    queryFn: () => fetchApi<{ status: string }>('/system/healthcheck'),
  })
}
```

### 技術スタック

- **Vite 6.x**: 高速ビルドツール
- **React 19.x**: UIライブラリ
- **TypeScript 5.x**: 型安全性
- **React Router 7.x**: クライアントサイドルーティング（BrowserRouter）
- **TanStack Query 5.x**: データフェッチ・キャッシュ
- **Tailwind CSS 4.x**: CSS-first設定（`@import 'tailwindcss'`のみ、postcss不要）
- **pnpm**: パッケージマネージャー

### ベストプラクティス

1. **API呼び出しは常に`/api`プレフィックス付き**
   ```typescript
   // ✅ GOOD
   fetch('/api/users')

   // ❌ BAD
   fetch('http://localhost:8000/users')  // 環境依存
   ```

2. **TanStack Queryを活用**
   - データフェッチ、キャッシュ、再検証を自動化
   - サーバー状態とクライアント状態を分離

3. **Tailwind CSS v4の使用**
   - `frontend/src/index.css`に`@import 'tailwindcss'`のみ
   - `vite.config.ts`に`@tailwindcss/vite`プラグイン追加
   - postcss/autoprefixerは不要

4. **型安全性の維持**
   - OpenAPI Generatorでバックエンドの型を自動生成可能
   - Zodでランタイムバリデーション

## 開発ワークフロー

### 新しいAPIエンドポイント追加

1. **Domainレイヤー**: 例外クラス定義（必要に応じて）
2. **Infrastructureレイヤー**: モデル作成
   ```python
   # app/infrastructure/database/models/your_model.py
   from .base import BaseModel

   class YourModel(BaseModel):
       __tablename__ = "your_table"
       # ...
   ```

3. **Presentationレイヤー**: スキーマ作成
   ```python
   # app/presentation/schemas/your_schema.py
   from pydantic import BaseModel

   class YourSchema(BaseModel):
       name: str
   ```

4. **Presentationレイヤー**: ルーター作成
   ```python
   # app/presentation/api/v1/your_router.py
   from fastapi import APIRouter, Depends
   from app.domain.exceptions.base import NotFoundError

   router = APIRouter()

   @router.get("/{item_id}")
   async def get_item(item_id: int, db: Session = Depends(get_db)):
       item = db.query(YourModel).filter_by(id=item_id).first()
       if not item:
           raise NotFoundError(f"Item {item_id} not found")
       return item
   ```

5. **Presentationレイヤー**: ルーター登録
   ```python
   # app/presentation/api/v1/__init__.py
   from .your_router import router as your_router

   api_router.include_router(your_router, prefix="/your-endpoint", tags=["your-endpoint"])
   ```

6. **マイグレーション**:
   ```bash
   make db:revision:create NAME="add_your_table"
   # アプリケーション起動時に自動適用
   ```

7. **テスト**:
   ```bash
   make test
   make type-check
   make lint
   ```

## 共通コンポーネント

### 依存性注入

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.presentation.api.deps import DBWithSession, get_db_with_session
from app.utils.schemas import SessionSchema
from app.presentation.api.deps import get_session, get_api_key

# DBセッションのみ
@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# セッションのみ
@router.get("/profile")
async def get_profile(session: SessionSchema = Depends(get_session)):
    user_id = session.data.get("user_id")
    # ...

# DB + セッション
@router.get("/protected")
async def protected(deps: DBWithSession = Depends(get_db_with_session)):
    user_id = deps.session.data.get("user_id")
    user = deps.db.query(User).filter_by(id=user_id).first()
    # ...

# API認証
@router.get("/api-protected")
async def api_protected(api_key: str = Depends(get_api_key)):
    # ...
```

### ロギング

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Info message")
logger.error("Error message", exc_info=True)
```

### 設定

```python
from app.core.config import get_settings

settings = get_settings()

database_url = settings.database_uri
is_production = settings.is_production
```

詳細: [docs/api-reference.md](docs/api-reference.md)

## ベストプラクティス

### 1. レイヤー分離の徹底

```python
# ❌ BAD: Presentation層でビジネスロジック
@router.post("/users")
async def create_user(user_data: UserCreate):
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")

# ✅ GOOD: Domain層で例外定義
from app.domain.exceptions.base import ValidationError

@router.post("/users")
async def create_user(user_data: UserCreate):
    if len(user_data.password) < 8:
        raise ValidationError("Password too short")
```

### 2. Domain例外の使用

```python
# ❌ BAD: HTTPExceptionを直接raise
raise HTTPException(status_code=404, detail="Not found")

# ✅ GOOD: Domain例外を使用
raise NotFoundError("User not found", details={"user_id": user_id})
```

### 3. ログイン時はセッションID再生成

```python
# ✅ GOOD: セッション固定攻撃対策
from app.utils.session_helper import regenerate_session_id

@router.post("/login")
async def login(...):
    user = authenticate(credentials)
    regenerate_session_id(db, request, response)
```

### 4. 機密情報はセッションに保存しない

```python
# ❌ BAD: パスワードを保存
session_data = {"password": user.password}

# ✅ GOOD: 最小限の識別情報のみ
session_data = {"user_id": user.id, "role": user.role}
```

### 5. 型ヒントの徹底（mypy strict mode）

```python
# ❌ BAD: 型ヒントなし
def get_user(user_id):
    return db.query(User).filter_by(id=user_id).first()

# ✅ GOOD: 厳格な型ヒント
from typing import Optional

def get_user(user_id: int) -> Optional[User]:
    return db.query(User).filter_by(id=user_id).first()
```

### 6. BaseModelの使用

```python
# ✅ GOOD: BaseModelを継承
from app.infrastructure.database.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    # id, created_at, updated_at は自動的に追加される
```

### 7. リストア前に差分確認

```bash
# ✅ GOOD: まず差分を確認
make db:backup:diff FILE="backup_xxx.backup.gz"
# 確認後にリストア
make db:backup:restore FILE="backup_xxx.backup.gz"
```

## 実装例（完全版）

### ユーザー管理API

```python
# app/infrastructure/database/models/user.py
from .base import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))


# app/presentation/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    class Config:
        from_attributes = True


# app/presentation/api/v1/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.database.models.user import User
from app.presentation.schemas.user import UserCreate, UserResponse
from app.domain.exceptions.base import NotFoundError, BadRequestError

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 重複チェック
    if db.query(User).filter_by(email=user_data.email).first():
        raise BadRequestError(
            "Email already exists",
            details={"email": user_data.email}
        )

    # パスワードハッシュ化（実際にはbcrypt等を使用）
    password_hash = hash_password(user_data.password)

    # ユーザー作成
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise NotFoundError(f"User {user_id} not found", details={"user_id": user_id})
    return user


# app/presentation/api/v1/__init__.py
from fastapi import APIRouter
from .users import router as users_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])


# マイグレーション作成
# make db:revision:create NAME="add_users_table"
```

## 重要な注意事項

1. **Makefileコマンド優先**: `make`コマンドが利用可能な場合は必ず使用
2. **Domain例外使用**: HTTPExceptionを直接raiseしない
3. **レイヤー分離厳守**: 依存関係ルールを遵守
4. **型ヒント必須**: mypy strict modeを通過すること
5. **BaseModel使用**: データベースモデルはBaseModelを継承
6. **セッション管理**: ログイン時はセッションID再生成
7. **バックアップ**: リストア前に必ず差分確認
8. **自動マイグレーション**: アプリケーション起動時に自動適用
9. **pre-commit hooks**: 自動的にコード品質チェックが実行される

## リファレンスドキュメント

- [README.md](README.md) - プロジェクト概要
- [docs/architecture.md](docs/architecture.md) - Clean Architecture詳細
- [docs/features/error-handling.md](docs/features/error-handling.md) - エラーハンドリング
- [docs/features/session-management.md](docs/features/session-management.md) - セッション管理
- [docs/features/database-backup.md](docs/features/database-backup.md) - バックアップシステム
- [docs/features/batch-system.md](docs/features/batch-system.md) - バッチ処理
- [docs/api-reference.md](docs/api-reference.md) - 共通コンポーネント
- [docs/deployment.md](docs/deployment.md) - デプロイメント
- [docs/secrets-management.md](docs/secrets-management.md) - シークレット管理
