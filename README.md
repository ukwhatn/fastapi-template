# FastAPI Template

FastAPIベースのプロダクション対応Webアプリケーションテンプレート。Clean Architecture（4層構造）、RDBベース暗号化セッション管理、Vite+React フロントエンド統合、包括的なDocker展開環境を提供。

## 技術スタック

**バックエンド**:
- FastAPI 0.120.0+, Python 3.13+
- SQLAlchemy 2.0+, PostgreSQL
- uv, Ruff, mypy strict, pytest

**フロントエンド**:
- Vite 6.x, React 19.x, TypeScript 5.x
- React Router 7.x, TanStack Query 5.x
- Tailwind CSS 4.x (CSS-first configuration)
- pnpm

**インフラ**:
- Docker Compose (multi-stage build, multi-profile)
- APScheduler, Sentry, New Relic

## クイックスタート

### 前提条件
- Docker & Docker Compose
- uv
- Python 3.13+
- Node.js 22+
- pnpm (corepack経由で自動インストール)

### 初期セットアップ

```bash
# 1. このテンプレートから新規リポジトリ作成
# GitHub UIで "Use this template" クリック

# 2. リポジトリをクローン
git clone https://github.com/yourusername/your-project.git
cd your-project

# 3. 環境変数ファイルを作成
make env

# 4. 必要に応じて .env を編集
nano .env

# 5. プロジェクトリネーム・依存関係をインストール
make dev:setup

# 6. フロントエンド依存関係をインストール
make frontend:install
```

### ローカル開発

```bash
# データベースサービスを起動
make local:up

# バックエンド + フロントエンドを並列起動（ホットリロード）
make local:serve

# または個別に起動
make local:serve:backend   # バックエンドのみ（ポート8000）
make local:serve:frontend  # フロントエンドのみ（ポート5173）
```

- APIドキュメント: http://localhost:8000/docs
- フロントエンド（開発）: http://localhost:5173
- フロントエンド（本番ビルド）: http://localhost:8000

### Docker使用

```bash
# データベース付きで起動
make up INCLUDE_DB=true

# ログを確認
make logs

# 停止
make down
```

## プロジェクト構造

```
.
├── app/                     # バックエンド（FastAPI）
│   ├── domain/              # Domain層（ビジネスロジック、例外定義）
│   ├── application/         # Application層（ユースケース、インターフェース）
│   ├── infrastructure/      # Infrastructure層（DB、リポジトリ実装）
│   │   ├── database/        # モデル、マイグレーション、バックアップ
│   │   ├── repositories/    # リポジトリ実装
│   │   ├── security/        # 暗号化、認証
│   │   └── batch/           # バッチタスク
│   ├── presentation/        # Presentation層（ルーター、スキーマ、ミドルウェア）
│   │   ├── api/             # APIエンドポイント
│   │   ├── schemas/         # Pydanticスキーマ
│   │   └── middleware/      # ミドルウェア
│   ├── core/                # 設定、ロギング
│   ├── utils/               # ユーティリティ、ヘルパー
│   └── main.py              # アプリケーションエントリーポイント
├── frontend/                # フロントエンド（Vite + React）
│   ├── src/
│   │   ├── pages/           # ページコンポーネント
│   │   ├── App.tsx          # ルーター設定
│   │   └── main.tsx         # エントリーポイント
│   ├── dist/                # ビルド成果物（本番）
│   ├── package.json         # Node依存関係
│   ├── pnpm-lock.yaml       # pnpmロックファイル
│   ├── vite.config.ts       # Vite設定（proxyなど）
│   └── tsconfig.json        # TypeScript設定
├── tests/                   # テスト
│   ├── unit/                # 単体テスト
│   └── integration/         # 統合テスト
├── docs/                    # ドキュメント
├── scripts/                 # デプロイスクリプト
├── Dockerfile               # マルチステージビルド（backend + frontend）
└── Makefile                 # タスク自動化
```

## コマンドリファレンス

### 開発

```bash
# セットアップ
make dev:setup              # 依存関係インストール
make env                    # .envファイル作成

# コード品質
make format                 # コードフォーマット
make lint                   # リント実行
make type-check             # 型チェック
make test                   # テスト実行
make test:cov               # カバレッジ付きテスト

# 開発サーバー
make local:up               # DBサービス起動
make local:serve            # バックエンド + フロントエンド並列起動
make local:serve:backend    # バックエンドのみ起動
make local:serve:frontend   # フロントエンドのみ起動
make local:down             # 停止
```

### フロントエンド

```bash
# 依存関係管理
make frontend:install       # 依存関係インストール
make frontend:build         # 本番ビルド

# コード品質
make frontend:lint          # ESLint実行
make frontend:lint:fix      # ESLint修正
make frontend:type-check    # TypeScriptチェック
```

### データベース

```bash
# マイグレーション
make db:revision:create NAME="description"  # マイグレーション作成
make db:migrate                             # マイグレーション適用
make db:current                             # 現在のリビジョン表示
make db:history                             # 履歴表示
make db:downgrade REV=-1                    # ロールバック

# バックアップ
make db:backup:oneshot                                # バックアップ作成
make db:backup:list                                   # ローカルバックアップ一覧
make db:backup:diff FILE="backup_xxx.backup.gz"       # 差分表示
make db:backup:restore FILE="backup_xxx.backup.gz"    # リストア

# S3バックアップ
make db:backup:list:remote                            # S3バックアップ一覧
make db:backup:restore:s3 FILE="backup_xxx.backup.gz" # S3からリストア
```

### デプロイ

```bash
# ローカルDocker
make up INCLUDE_DB=true     # 起動
make down                   # 停止
make reload                 # 再起動

# 開発環境（自動デプロイ via GitHub Actions）
# develop ブランチへのプッシュで自動デプロイ
git push origin develop

# 本番環境（自動デプロイ via GitHub Actions）
# main ブランチへのプッシュで自動デプロイ
git push origin main
```

### シークレット管理

```bash
# SOPS + age による暗号化
make secrets:encrypt:dev    # Dev環境変数を暗号化
make secrets:encrypt:prod   # Prod環境変数を暗号化
make secrets:edit:dev       # Dev環境変数を編集（自動再暗号化）
make secrets:edit:prod      # Prod環境変数を編集（自動再暗号化）
```

## ドキュメント

### アーキテクチャ・設計
- [Architecture](docs/architecture.md) - Clean Architecture実装詳細、レイヤー分離

### 機能詳細
- [Error Handling](docs/features/error-handling.md) - エラーハンドリング機構
- [Session Management](docs/features/session-management.md) - RDBベースセッション管理
- [Database Backup](docs/features/database-backup.md) - バックアップシステム
- [Batch System](docs/features/batch-system.md) - バッチ処理

### リファレンス
- [API Reference](docs/api-reference.md) - 共通コンポーネント、ヘルパー関数

### 運用
- [Deployment](docs/deployment.md) - Local/Dev/Prod環境デプロイ
- [Secrets Management](docs/secrets-management.md) - SOPS + ageによるシークレット管理

## 開発ワークフロー

### 新しいAPIエンドポイントを追加

1. **Domainレイヤー**：例外クラスを定義（必要に応じて）
   ```python
   # app/domain/exceptions/your_exceptions.py
   from .base import DomainError

   class YourCustomError(DomainError):
       def __init__(self, message: str = "Custom error"):
           super().__init__(message=message, code="your_custom_error")
   ```

2. **Infrastructureレイヤー**：モデルとリポジトリを実装
   ```python
   # app/infrastructure/database/models/your_model.py
   from .base import BaseModel
   from sqlalchemy.orm import Mapped, mapped_column

   class YourModel(BaseModel):
       __tablename__ = "your_table"
       name: Mapped[str] = mapped_column(String(100))
   ```

3. **Presentationレイヤー**：スキーマとルーターを実装
   ```python
   # app/presentation/schemas/your_schema.py
   from pydantic import BaseModel

   class YourSchema(BaseModel):
       name: str
   ```

4. **マイグレーション**
   ```bash
   make db:revision:create NAME="add_your_table"
   # マイグレーションファイルを確認・編集
   # アプリケーション起動時に自動適用される
   ```

5. **テスト**
   ```bash
   make test
   make type-check
   make lint
   ```

### コミット前チェック

pre-commit hooksが自動的に以下を実行：
- Ruff format（コードフォーマット）
- Ruff lint --fix（リント修正）
- mypy（型チェック、pushフック）
- pytest（テスト、pushフック）

手動実行：
```bash
make pre-commit:run         # 全フックを実行
```

インストール：
```bash
make pre-commit:install     # 初回のみ
```

## ライセンス

MIT License
