# FastAPI Template

[FastAPI](https://fastapi.tiangolo.com/)を使用したWebアプリケーション開発用テンプレート。

## ✨ 機能

- **🚀 高速開発**: 構造化されたテンプレート、ホットリロード、包括的なツール群
- **🏗️ モジュラーアーキテクチャ**: クリーンなAPI設計とバージョン管理
- **🗄️ データベース統合**: SQLAlchemy、PostgreSQL、Redis対応、マイグレーション管理
- **🐳 Docker対応**: Docker Composeによる完全なコンテナ化
- **🔒 セキュリティ重視**: BanditとSemgrepによる組み込みセキュリティスキャン
- **📊 監視機能**: Sentry統合、New Relic APM、構造化ログ
- **🧪 コード品質**: Ruffによる自動リント、フォーマット、型チェック

## 🚀 クイックスタート

### 1. プロジェクトを作成

1. このテンプレートを使用して新しいリポジトリを作成
2. リポジトリをクローン:
   ```bash
   git clone https://github.com/yourusername/your-api-name.git
   cd your-api-name
   ```

### 2. プロジェクトを初期化

```bash
# プロジェクト名を設定
make project:init NAME="あなたのプロジェクト名"

# 環境ファイルをセットアップ
make env

# 依存関係をインストール
make dev:setup
```

### 3. APIサーバーを実行

**ローカル開発（推奨 - ホットリロード付き）:**
```bash
# データベースサービスを起動
make local:up

# アプリケーションをuvでネイティブ実行
make local:serve
# または: uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

**Docker使用:**
```bash
# データベース付きで起動
make up INCLUDE_DB=true
```

APIサーバーが起動しました！ 🎉

- **API文書**: http://localhost:8000/docs
- **管理画面**: http://localhost:8001 (Adminer - データベース管理)

## 📚 ドキュメント

- **[開発ガイド](development.md)** - API構築、データベース操作、Docker開発の完全ガイド
- **[デプロイメントガイド](docs/deployment.md)** - Local/Dev/Prod環境へのデプロイ方法
- **[シークレット管理ガイド](docs/secrets-management.md)** - SOPS + ageによる安全なシークレット管理
- **[クイックリファレンス](#クイックリファレンス)** - 開発に必要なコマンド一覧

## 🏗️ アーキテクチャ概要

```
app/
├── main.py              # FastAPIエントリーポイント
├── api/                 # APIエンドポイント（バージョン管理）
├── core/config.py       # 設定管理
├── db/                  # データベース層（モデル、スキーマ、CRUD）
├── static/              # 静的ファイル（CSS、JS、画像など）
├── templates/           # Jinja2テンプレート（HTMLファイル）
└── utils/               # ユーティリティ関数とヘルパー
```

**主要機能:**
- **構造化されたテンプレート**: モデル、スキーマ、CRUD、ルーターの明確な分離
- **データベース層**: モデル、スキーマ、CRUD操作のクリーンな分離
- **設定システム**: Pydanticバリデーション付き環境ベース設定
- **エラーハンドリング**: 包括的なエラートラッキングとユーザーフレンドリーな応答

## 🛠️ 使用技術

- **[FastAPI](https://fastapi.tiangolo.com/)** - モダンで高速なPython Webフレームワーク
- **[SQLAlchemy](https://sqlalchemy.org/)** - マイグレーション対応データベースORM
- **[Pydantic](https://pydantic.dev/)** - データバリデーションと設定管理
- **[uv](https://github.com/astral-sh/uv)** - Pythonパッケージ管理
- **[Ruff](https://github.com/astral-sh/ruff)** - 超高速リントとフォーマット

## クイックリファレンス

### 必須コマンド

```bash
# 開発セットアップ
make dev:setup          # 全依存関係をインストール
make env                # テンプレートから.envファイルを作成

# コード品質
make format             # Ruffでコードをフォーマット
make lint               # コード品質をチェック
make type-check         # mypy型チェック
make security:scan      # セキュリティ分析を実行
make test               # テストを実行
make test:cov           # カバレッジ付きテスト

# ローカル開発（uv native + Docker DB）
make local:up           # データベースサービス起動
make local:serve        # アプリケーション起動（ホットリロード）
make local:down         # サービス停止

# Docker操作（レガシー）
make up INCLUDE_DB=true # データベース付きで起動
make down               # 全コンテナを停止
make logs               # コンテナログを表示

# デプロイ（新規）
make dev:deploy         # Dev環境デプロイ（Watchtower自動更新）
make prod:deploy        # 本番環境デプロイ（確認付き）
make watchtower:setup   # Watchtowerセットアップ（サーバーごとに1回）

# シークレット管理（SOPS + age）
make secrets:encrypt:dev   # Dev環境変数を暗号化
make secrets:encrypt:prod  # Prod環境変数を暗号化
make secrets:edit:dev      # Dev環境変数を編集（自動再暗号化）
make secrets:edit:prod     # Prod環境変数を編集（自動再暗号化）

# データベース
make db:migrate         # データベースマイグレーションを適用
make db:revision:create NAME="説明" # 新しいマイグレーションを作成
make db:current         # 現在のリビジョンを表示
make db:history         # マイグレーション履歴を表示
```

### 機能追加

1. **APIエンドポイントを作成**: 
   - `app/db/models/`にモデルを作成
   - `app/db/schemas/`にスキーマを作成
   - `app/db/crud/`にCRUD操作を作成
   - `app/api/v1/`にルーターを作成
2. **ルーターを登録**: `app/api/v1/__init__.py`にルーターを追加
3. **マイグレーション**: `make db:revision:create NAME="add_model"`
4. **テスト**: 開発中は`make reload`でホットリロード

各側面の詳細なチュートリアルは[開発ガイド](development.md)を参照してください。

## 🤝 コントリビューション

1. リポジトリをフォーク
2. 機能ブランチを作成
3. 変更を加える
4. テストとリントを実行: `make lint && make security:scan`
5. プルリクエストを送信

## 📄 ライセンス

このテンプレートはオープンソースで、[MITライセンス](LICENSE)の下で利用可能です。
