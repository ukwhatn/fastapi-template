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
make envs:setup

# 依存関係をインストール
make dev:setup
```

### 3. APIサーバーを実行

**ローカル開発:**
```bash
cd app && python main.py
```

**Docker使用（推奨）:**
```bash
# データベースとRedisと一緒にAPIを起動（不要ならfalseにする）
make up INCLUDE_DB=true INCLUDE_REDIS=true
```

APIサーバーが起動しました！ 🎉

- **API文書**: http://localhost:8000/docs
- **管理画面**: http://localhost:8080 (Adminer - データベース管理)

## 📚 ドキュメント

- **[開発ガイド](development.md)** - API構築、データベース操作、Docker開発の完全ガイド
- **[クイックリファレンス](#クイックリファレンス)** - 開発に必要なコマンド一覧

## 🏗️ アーキテクチャ概要

```
app/
├── main.py              # FastAPIエントリーポイント
├── api/                 # APIエンドポイント（バージョン管理）
├── core/config.py       # 設定管理
├── db/                  # データベース層（モデル、スキーマ、CRUD）
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
# 開発
make dev:setup          # 全依存関係をインストール
make envs:setup         # テンプレートから環境ファイルを作成

# コード品質
make format            # Ruffでコードをフォーマット
make lint              # コード品質をチェック
make security:scan     # セキュリティ分析を実行

# Docker操作
make up                # APIサーバーを起動
make up INCLUDE_DB=true # データベース付きで起動
make logs              # コンテナログを表示
make down              # 全コンテナを停止

# データベース
make db:migrate        # データベースマイグレーションを適用
make db:revision:create NAME="説明" # 新しいマイグレーションを作成
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
