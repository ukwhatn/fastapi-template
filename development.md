# 開発ガイド

このガイドでは、fastapi-templateを使用してFastAPI Webアプリケーションを作成するための完全な開発ワークフローを説明します。

## 目次

1. [初期セットアップ](#初期セットアップ)
2. [開発環境](#開発環境)
3. [プロジェクト構造](#プロジェクト構造)
4. [APIエンドポイントの作成](#apiエンドポイントの作成)
5. [データベース操作](#データベース操作)
6. [静的ファイルとテンプレート](#静的ファイルとテンプレート)
7. [設定管理](#設定管理)
8. [Docker開発](#docker開発)
9. [コード品質とテスト](#コード品質とテスト)

---

## 初期セットアップ

### 1. テンプレートからリポジトリを作成

1. テンプレートリポジトリにアクセス
2. "Use this template" → "Create a new repository"をクリック
3. リポジトリ名と設定を選択
4. 新しいリポジトリをクローン:
   ```bash
   git clone https://github.com/yourusername/your-api-name.git
   cd your-api-name
   ```

### 2. プロジェクトの初期化

```bash
make project:init NAME="あなたのプロジェクト名"
```

このコマンドは、プロジェクト名を指定された名前に変更し、新しいGitブランチ（develop）を作成します。

### 3. 環境セットアップ

1. **uv（Pythonパッケージマネージャー）をインストール**:
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # pipを使用する場合
   pip install uv
   ```

2. **環境ファイルをセットアップ**:
   ```bash
   make envs:setup
   ```
   これにより`envs/`ディレクトリのテンプレートから環境ファイルが作成されます。

3. **環境変数を設定**:
   - `server.env`を編集 - API設定を追加
   - `db.env`を編集 - データベース認証情報を設定
   - 必要に応じて他の`.env`ファイルも編集

4. **依存関係をインストール**:
   ```bash
   make dev:setup
   ```

---

## 開発環境

### ローカル開発（Dockerなし）

データベースなしでのシンプルなAPI開発の場合:

```bash
# 依存関係をインストール
make dev:setup

# 環境変数を直接設定または.envファイルを使用
export ENV_MODE="development"

# APIサーバーを実行
cd app && python main.py
```

### Docker開発（推奨）

データベースとRedisを含むフルスタック開発の場合:

```bash
# 全サービス（API、データベース、Redis）を起動
make up INCLUDE_DB=true INCLUDE_REDIS=true

# またはAPIのみを起動
make up

# ログを確認
make logs

# サービスを停止
make down
```

### 開発コマンド

- `make lint` - コード品質をチェック
- `make format` - コードをフォーマット
- `make security:scan` - セキュリティスキャンを実行

---

## プロジェクト構造

```
app/
├── main.py              # FastAPIアプリケーションエントリーポイント
├── core/
│   ├── config.py        # 設定管理
│   ├── exceptions.py    # カスタム例外定義
│   └── middleware.py    # カスタムミドルウェア
├── api/                 # APIエンドポイント
│   ├── deps.py          # 依存性注入
│   ├── system/          # システム関連エンドポイント
│   └── v1/              # バージョン1のAPIエンドポイント
├── db/                  # データベース層
│   ├── models/          # SQLAlchemyモデル
│   ├── schemas/         # Pydanticスキーマ
│   ├── crud/            # データベース操作
│   └── connection.py    # データベース接続
├── static/              # 静的ファイル（CSS、JS、画像など）
├── templates/           # Jinja2テンプレート（HTMLファイル）
└── utils/               # ユーティリティモジュール
```

---

## APIエンドポイントの作成

FastAPIでは、エンドポイントをルーターとして整理します。新しいリソース（例：ブログ投稿）を作成する完全な手順を説明します。

### 1. データベースモデルを作成

**`app/db/models/blog_post.py`を作成**:

```python
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel

class BlogPost(BaseModel):
    __tablename__ = "blog_posts"
    
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    # リレーションシップ（必要に応じて）
    # author = relationship("User", back_populates="blog_posts")
```

### 2. Pydanticスキーマを作成

**`app/db/schemas/blog_post.py`を作成**:

```python
from typing import Optional
from datetime import datetime
from .base import BaseModelSchema, BaseSchema

class BlogPostBase(BaseSchema):
    title: str
    content: str
    published: bool = False
    author_id: int

class BlogPostCreate(BlogPostBase):
    pass

class BlogPostUpdate(BlogPostBase):
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None
    author_id: Optional[int] = None

class BlogPost(BlogPostBase, BaseModelSchema):
    pass
```

### 3. CRUD操作を作成

**`app/db/crud/blog_post.py`を作成**:

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from .base import CRUDBase
from db.models.blog_post import BlogPost
from db.schemas.blog_post import BlogPostCreate, BlogPostUpdate

class CRUDBlogPost(CRUDBase[BlogPost, BlogPostCreate, BlogPostUpdate]):
    def get_by_author(self, db: Session, author_id: int) -> List[BlogPost]:
        return db.query(BlogPost).filter(BlogPost.author_id == author_id).all()
    
    def get_published(self, db: Session, skip: int = 0, limit: int = 100) -> List[BlogPost]:
        return (
            db.query(BlogPost)
            .filter(BlogPost.published == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search(
        self, 
        db: Session, 
        query: str, 
        category: Optional[str] = None,
        published: bool = True
    ) -> List[BlogPost]:
        q = db.query(BlogPost).filter(BlogPost.title.contains(query))
        if published:
            q = q.filter(BlogPost.published == True)
        return q.all()

blog_post = CRUDBlogPost(BlogPost)
```

### 4. APIルーターを作成

**`app/api/v1/blog_posts.py`を作成**:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.deps import get_db
from db.crud.blog_post import blog_post
from db.schemas.blog_post import BlogPost, BlogPostCreate, BlogPostUpdate

router = APIRouter()

@router.get("/", response_model=List[BlogPost])
def read_blog_posts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """ブログ投稿一覧を取得"""
    posts = blog_post.get_multi(db, skip=skip, limit=limit)
    return posts

@router.post("/", response_model=BlogPost)
def create_blog_post(
    post_in: BlogPostCreate,
    db: Session = Depends(get_db)
):
    """新しいブログ投稿を作成"""
    return blog_post.create(db=db, obj_in=post_in)

@router.get("/{post_id}", response_model=BlogPost)
def read_blog_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """特定のブログ投稿を取得"""
    db_post = blog_post.get(db, id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return db_post

@router.put("/{post_id}", response_model=BlogPost)
def update_blog_post(
    post_id: int,
    post_in: BlogPostUpdate,
    db: Session = Depends(get_db)
):
    """ブログ投稿を更新"""
    db_post = blog_post.get(db, id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return blog_post.update(db=db, db_obj=db_post, obj_in=post_in)

@router.delete("/{post_id}")
def delete_blog_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """ブログ投稿を削除"""
    db_post = blog_post.get(db, id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Blog post not found")
    blog_post.remove(db=db, id=post_id)
    return {"message": "Blog post deleted successfully"}

@router.get("/search/", response_model=List[BlogPost])
def search_blog_posts(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    category: Optional[str] = Query(None, description="カテゴリフィルター"),
    published: bool = Query(True, description="公開済みのみ"),
    db: Session = Depends(get_db)
):
    """ブログ投稿を検索"""
    return blog_post.search(db, query=q, category=category, published=published)
```

### 5. ルーターを登録

**`app/api/v1/__init__.py`を編集してルーターを追加**:

```python
from fastapi import APIRouter
from api.v1 import blog_posts  # 新しく追加

api_router = APIRouter()

# 既存のルーター
# api_router.include_router(...)

# 新しいルーターを追加
api_router.include_router(
    blog_posts.router,
    prefix="/blog_posts",
    tags=["BlogPosts"]
)
```

### 6. マイグレーションを作成・適用

```bash
# 新しいマイグレーションを作成
make db:revision:create NAME="add_blog_post_table"

# マイグレーションを適用
make db:migrate
```

### 7. 高度なエンドポイント機能

**ファイルアップロード**:
```python
from fastapi import File, UploadFile

@router.post("/{post_id}/upload-image/")
async def upload_blog_image(
    post_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """ブログ投稿に画像をアップロード"""
    # ファイル処理ロジック
    return {"filename": file.filename, "post_id": post_id}
```

**認証が必要なエンドポイント**:
```python
from api.deps import get_current_user

@router.post("/", response_model=BlogPost)
def create_blog_post(
    post_in: BlogPostCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)  # 認証が必要
):
    """新しいブログ投稿を作成（認証必須）"""
    post_in.author_id = current_user.id
    return blog_post.create(db=db, obj_in=post_in)
```

---

## データベース操作

### 1. マイグレーション管理

```bash
# 新しいマイグレーションを作成
make db:revision:create NAME="add_blog_post_table"

# マイグレーションを適用
make db:migrate

# 現在のマイグレーションを確認
make db:current

# マイグレーション履歴を表示
make db:history
```

### 2. 複雑なクエリの例

```python
# app/db/crud/blog_post.py に追加
def get_posts_with_stats(self, db: Session) -> List[dict]:
    """投稿数の統計付きでブログ投稿を取得"""
    return (
        db.query(
            BlogPost.author_id,
            func.count(BlogPost.id).label('post_count'),
            func.max(BlogPost.created_at).label('latest_post')
        )
        .group_by(BlogPost.author_id)
        .all()
    )
```

---

## 静的ファイルとテンプレート

このテンプレートは静的ファイルサーブとJinja2テンプレートの自動有効化機能を提供します。

### 1. 静的ファイルの使用

**静的ファイルを配置**:
```bash
# CSSファイルを配置
mkdir -p app/static/css
echo "body { font-family: Arial, sans-serif; }" > app/static/css/style.css

# JavaScriptファイルを配置
mkdir -p app/static/js
echo "console.log('Hello, FastAPI!');" > app/static/js/app.js

# 画像ファイルを配置
mkdir -p app/static/images
# 画像ファイルをapp/static/images/にコピー
```

**静的ファイルへのアクセス**:
- CSS: `http://localhost:8000/static/css/style.css`
- JavaScript: `http://localhost:8000/static/js/app.js`
- 画像: `http://localhost:8000/static/images/logo.png`

### 2. Jinja2テンプレートの使用

**テンプレートファイルを作成**:

**`app/templates/base.html`**:
```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ title }}{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <h1>{% block header %}FastAPI Template{% endblock %}</h1>
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
    <script src="/static/js/app.js"></script>
</body>
</html>
```

**`app/templates/index.html`**:
```html
{% extends "base.html" %}

{% block title %}{{ title }} - ホーム{% endblock %}

{% block content %}
<div class="container">
    <h2>ようこそ</h2>
    <p>FastAPIテンプレートへようこそ！</p>
    
    {% if user %}
        <p>こんにちは、{{ user.name }}さん！</p>
    {% else %}
        <p>ゲストユーザーとしてアクセスしています。</p>
    {% endif %}
</div>
{% endblock %}
```

### 3. テンプレートを使用するエンドポイント

**`app/api/v1/pages.py`を作成**:

```python
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from utils import get_templates
from api.deps import get_db
from db.crud.blog_post import blog_post

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """ホームページ"""
    templates = get_templates(request)
    if templates is None:
        return HTMLResponse("<h1>Templates not enabled</h1>")
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "FastAPI Template"}
    )

@router.get("/blog/", response_class=HTMLResponse)
async def blog_list_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """ブログ一覧ページ"""
    templates = get_templates(request)
    if templates is None:
        return HTMLResponse("<h1>Templates not enabled</h1>")
    
    posts = blog_post.get_published(db)
    
    return templates.TemplateResponse(
        "blog/list.html",
        {
            "request": request,
            "title": "ブログ一覧",
            "posts": posts
        }
    )
```

### 4. 自動有効化の仕組み

- **静的ファイル**: `app/static/`ディレクトリに`.keep`以外のファイルがあると自動的に`/static`でマウント
- **テンプレート**: `app/templates/`ディレクトリに`.keep`以外のファイルがあると自動的にJinja2Templates有効化
- **アクセス**: `utils.get_templates(request)`でテンプレートインスタンスを取得

### 5. テンプレートでの動的コンテンツ

**条件分岐とループ**:
```html
{% if posts %}
    <ul>
    {% for post in posts %}
        <li>
            <h3>{{ post.title }}</h3>
            <p>{{ post.content[:100] }}...</p>
            <small>投稿日: {{ post.created_at.strftime('%Y-%m-%d') }}</small>
        </li>
    {% endfor %}
    </ul>
{% else %}
    <p>投稿がありません。</p>
{% endif %}
```

**フォーム処理**:
```html
<form method="post" action="/api/v1/blog_posts/">
    <div>
        <label for="title">タイトル:</label>
        <input type="text" id="title" name="title" required>
    </div>
    <div>
        <label for="content">内容:</label>
        <textarea id="content" name="content" required></textarea>
    </div>
    <button type="submit">投稿</button>
</form>
```

---

## 設定管理

### 1. 環境変数

アプリケーションは集約設定に`app/core/config.py`を使用します:

```python
# core/config.pyに新しい設定を追加
class Settings(BaseSettings):
    # 新しい設定
    API_KEY: str = ""
    FEATURE_ENABLED: bool = True
    MAX_ITEMS: int = 100
    UPLOAD_DIR: str = "/tmp/uploads"
```

### 2. APIでの設定使用

```python
from core import get_settings

@router.get("/config/")
def show_config():
    settings = get_settings()
    if settings.FEATURE_ENABLED:
        return {"message": f"機能が有効です！最大アイテム数: {settings.MAX_ITEMS}"}
    else:
        return {"message": "機能は無効です"}
```

### 3. 環境固有の設定

`ENV_MODE`を設定して動作を制御:

```python
from core import get_settings

settings = get_settings()

if settings.is_development:
    # 開発用コード
    logger.debug("デバッグ情報")

if settings.is_production:
    # 本番用コード
    await send_error_to_monitoring()
```

---

## Docker開発

### 1. データベースとの開発

```bash
# データベースとRedisと一緒に起動
make up INCLUDE_DB=true INCLUDE_REDIS=true

# Adminer（Webインターフェース）でデータベースにアクセス
# http://localhost:8080 にアクセス
# サーバー: db, ユーザー名/パスワード: db.envから

# データベースマイグレーションを実行
make db:migrate
```

### 2. Docker Composeプロファイル

`compose.yml`は起動するサービスを制御するためにプロファイルを使用:

- **app**: FastAPIアプリケーション（常に含まれる）
- **db**: PostgreSQLデータベース（`INCLUDE_DB=true`で含める）
- **redis**: Redisキャッシュ（`INCLUDE_REDIS=true`で含める）
- **dev**: Adminerなどの開発ツール

### 3. カスタムDockerコマンド

```bash
# 再ビルドして再起動
make reload

# 特定のサービスのログを表示
docker compose logs app -f

# コンテナ内でコマンドを実行
docker compose exec app python -c "from core import get_settings; print(get_settings().DATABASE_URI)"
```

---

## コード品質とテスト

### 1. コード品質ツール

```bash
# コードをリント（問題をチェック）
make lint

# リント問題を自動修正
make lint:fix

# コードをフォーマット
make format

# セキュリティスキャン
make security:scan
```

### 2. プリコミットワークフロー

コードをコミットする前に:

```bash
# フォーマットとリント
make format
make lint

# セキュリティスキャンを実行
make security:scan

# 変更をコミット
git add .
git commit -m "feat: 新機能を追加"
```

### 3. テストの追加（オプション）

テストを追加したい場合は、テストフレームワークを作成:

1. `pyproject.toml`にテスト依存関係を追加:
   ```toml
   dev = [
       "pytest>=8.3.5",
       "pytest-asyncio>=0.21.0",
       "httpx>=0.24.0",  # FastAPIテスト用
       # ... 既存のdev依存関係
   ]
   ```

2. テスト構造を作成:
   ```
   tests/
   ├── conftest.py
   ├── test_api/
   └── test_db/
   ```

3. `Makefile`にテストコマンドを追加:
   ```makefile
   test:
   	uv run pytest tests/
   ```

---

## 一般的なパターン

### 1. 認証と認可

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(token: str = Depends(security)):
    # トークン検証ロジック
    if not verify_token(token.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return get_user_from_token(token.credentials)

@router.get("/protected/")
def protected_endpoint(current_user = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.username}!"}
```

### 2. エラーハンドリング

```python
from core.exceptions import APIError

@router.post("/process/")
async def process_data(data: dict):
    try:
        result = await complex_operation(data)
        return {"result": result}
    except ValueError as e:
        raise APIError(
            status_code=400,
            code="invalid_data",
            message=f"データが無効です: {str(e)}"
        )
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        raise APIError(
            status_code=500,
            code="internal_error",
            message="内部エラーが発生しました"
        )
```

### 3. バックグラウンドタスク

```python
from fastapi import BackgroundTasks

def send_email_notification(email: str, message: str):
    # メール送信ロジック
    pass

@router.post("/send-notification/")
def create_notification(
    email: str,
    message: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_email_notification, email, message)
    return {"message": "通知が送信されます"}
```

### 4. OpenAPI文書のカスタマイズ

```python
@router.post(
    "/",
    response_model=BlogPost,
    summary="ブログ投稿を作成",
    description="新しいブログ投稿を作成します。タイトルと内容は必須です。",
    response_description="作成されたブログ投稿",
    responses={
        400: {"description": "無効なリクエストデータ"},
        500: {"description": "内部サーバーエラー"}
    }
)
def create_blog_post(post_in: BlogPostCreate):
    # 実装
    pass
```

この開発ガイドは、このテンプレートを使用してFastAPI Webアプリケーションの構築を始めるのに役立ちます。各セクションでは、特定のニーズに適応できる実用的な例を提供しています。 