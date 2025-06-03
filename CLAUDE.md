# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## プロジェクト概要

FastAPIで構築されたWebアプリケーションテンプレートで、プロダクション対応のAPIサーバーの基盤を提供します。モジュラーアーキテクチャ、自動ルーター生成、SQLAlchemyによるデータベース統合、Redis対応、包括的なDockerデプロイメントを使用します。

## ドキュメント構造

- **README.md**: ユーザー向けランディングページ（日本語）
- **development.md**: 完全な開発ガイド（日本語）- API作成、モデル定義、データベース操作、Docker開発
- **CLAUDE.md**: AI開発アシスタント向けプロジェクト情報

## 開発コマンド

### 環境セットアップ
- `make dev:setup` - uvを使用して全依存関係をインストール（server, db, devグループ）
- `make envs:setup` - envs/ディレクトリから環境ファイルテンプレートをコピー

### コード品質
- `make lint` - Ruffリンターでコード品質をチェック
- `make lint:fix` - 自動修正付きでRuffを実行
- `make format` - Ruffフォーマッターでコードフォーマット

### Docker操作
- `make up` - 全コンテナをデタッチモードでビルド・起動
- `make down` - 全コンテナを停止
- `make reload` - コンテナを再ビルドして再起動
- `make logs` - コンテナログをフォロー
- `make ps` - 実行中のコンテナを表示

### データベース管理
- `make db:revision:create NAME="説明"` - 新しいAlembicマイグレーションを作成
- `make db:migrate` - データベースにマイグレーションを適用
- `make db:current` - 現在のマイグレーションリビジョンを表示
- `make db:history` - マイグレーション履歴を表示

### リソース生成
- `make model:generate NAME=resource_name` - モデル、CRUD、スキーマファイルを生成
- `make router:generate NAME=resource_name` - APIルーターファイルを生成

### セキュリティスキャン
- `make security:scan` - 全セキュリティスキャンを実行（Bandit + Semgrep）
- `make security:scan:code` - Bandit静的解析を実行
- `make security:scan:sast` - Semgrepセキュリティ解析を実行

## アーキテクチャ

### コアコンポーネント
- **main.py**: FastAPIアプリケーションエントリーポイント、ミドルウェア設定、エラーハンドリング
- **core/config.py**: Pydanticを使用した環境ベース設定の集約設定
- **api/**: APIルーターとエンドポイント定義
- **db/**: SQLAlchemyモデル、スキーマ、CRUD操作を含むデータベース層

### 設定システム
アプリケーションはPydanticベースの設定システム（`core/config.py`）を使用し、以下をサポート:
- 環境固有設定（`ENV_MODE`による development/production/test）
- データベース接続管理（PostgreSQL）
- Redis統合
- Sentryエラートラッキング
- New Relic APM監視
- セキュリティヘッダーとCSPポリシー

### データベースアーキテクチャ
- **models/base.py**: 自動インクリメントIDと created_at/updated_at用の`TimeStampMixin`を持つ`BaseModel`を提供
- **models/**: `BaseModel`を継承するSQLAlchemyモデル定義
- **schemas/**: データバリデーション用Pydanticスキーマ
- **crud/**: ベースCRUD操作を持つデータベース操作層

### APIアーキテクチャ
- **api/v1/**: バージョン管理されたAPIエンドポイント
- **api/system/**: システム関連エンドポイント（ヘルスチェック等）
- **api/deps.py**: 依存性注入用の共通依存関数
- 自動OpenAPI/Swagger文書生成

### Docker設定
プロジェクトはマルチプロファイルDocker Compose設定を使用:
- **app**: メインFastAPIアプリケーションサービス
- **db**: ヘルスチェック付きPostgreSQLデータベース
- **redis**: Redisキャッシュ/セッションストア
- **db-migrator**: Alembicマイグレーションランナー
- **adminer**: データベース管理インターフェース（開発のみ）
- **db-dumper**: データベースバックアップユーティリティ

環境変数が`INCLUDE_DB`と`INCLUDE_REDIS`フラグによってどのサービスが含まれるかを制御します。

## 開発ワークフロー

1. `make envs:setup`でテンプレートから環境ファイルを作成
2. 各環境ファイルでデータベースとAPI設定を構成
3. `make dev:setup`で依存関係をインストール
4. `make up INCLUDE_DB=true`でデータベース付きで起動
5. `make db:migrate`でデータベースマイグレーションを適用
6. コミット前に`make lint`と`make format`を使用

## 主要ファイル

- `app/main.py:1-210` - FastAPIアプリケーション設定とミドルウェア
- `app/core/config.py` - 環境設定とPydantic設定クラス
- `app/db/models/base.py` - タイムスタンプMixin付きベースモデル
- `app/api/__init__.py` - APIルーター統合
- `templates/generate.py` - リソース生成スクリプト

## 典型的な開発タスク

### 新しいAPIエンドポイントを作成
1. `make model:generate NAME=blog_post`でモデル、CRUD、スキーマを生成
2. `make router:generate NAME=blog_post`でAPIルーターを生成
3. `app/api/v1/__init__.py`にルーターを登録
4. `make db:revision:create NAME="add_blog_post"`でマイグレーションを作成
5. `make db:migrate`で適用

### データベースモデルを追加
1. `app/db/models/`に新しいモデルファイルを作成
2. `app/db/schemas/`に対応するPydanticスキーマを作成
3. `app/db/crud/`にCRUD操作を作成
4. `make db:revision:create NAME="add_model"`でマイグレーションを作成
5. `make db:migrate`で適用

### 環境設定を追加
1. `app/core/config.py`の`Settings`クラスに新しいフィールドを追加
2. 必要に応じて対応する`.env`ファイルを更新
3. APIエンドポイントで`get_settings()`を使用してアクセス

### ミドルウェアを追加
1. `app/core/middleware.py`に新しいミドルウェアクラスを作成
2. `app/main.py`でミドルウェアを登録

## テスト

プロジェクトにはセキュリティスキャンが含まれていますが、明示的なテストフレームワークは設定されていません。テストを追加する場合は、プロジェクト構造を確認し、`pyproject.toml`の`dev`グループに適切なテスト依存関係を追加してください。

## 監視とエラーハンドリング

- Sentry統合によるエラートラッキング
- New Relic APM監視（本番環境）
- 構造化ログ出力
- カスタム例外ハンドリング（`core/exceptions.py`）
- ヘルスチェックエンドポイント 