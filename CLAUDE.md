# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## プロジェクト概要

FastAPIで構築されたWebアプリケーションテンプレートで、プロダクション対応のAPIサーバーの基盤を提供します。Clean Architecture（4層）、SQLAlchemyによるデータベース統合、RDBベースのセッション管理（暗号化対応）、包括的なDockerデプロイメントを使用します。Supabase対応。

## ドキュメント構造

- **README.md**: ユーザー向けランディングページ（日本語）
- **development.md**: 完全な開発ガイド（日本語）- API作成、モデル定義、データベース操作、Docker開発
- **CLAUDE.md**: AI開発アシスタント向けプロジェクト情報

## 開発コマンド

### 環境セットアップ
- `make dev:setup` - uvを使用して全依存関係をインストール
- `make env` - .env.exampleから.envファイルを作成

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

### セキュリティスキャン
- `make security:scan` - 全セキュリティスキャンを実行（Bandit + Semgrep）
- `make security:scan:code` - Bandit静的解析を実行
- `make security:scan:sast` - Semgrepセキュリティ解析を実行

### テスト
- `make test` - 全テストを実行
- `make test:cov` - カバレッジレポート付きでテストを実行

## アーキテクチャ

Clean Architecture（4層）を採用:

### Domain層 (`app/domain/`)
- **exceptions/**: ビジネスルール例外（APIError, ValidationErrorなど）
- **entities/**: ドメインエンティティ
- **value_objects/**: 値オブジェクト

### Application層 (`app/application/`)
- **use_cases/**: ユースケース実装
- **services/**: アプリケーションサービス
- **interfaces/**: リポジトリインターフェース
- **dtos/**: Data Transfer Objects

### Infrastructure層 (`app/infrastructure/`)
- **database/**: SQLAlchemyモデル、接続管理
- **repositories/**: リポジトリ実装（SessionServiceなど）
- **security/**: セキュリティ実装（暗号化、フィンガープリント）
- **external/**: 外部API連携

### Presentation層 (`app/presentation/`)
- **api/**: FastAPI ルーター（v1, system）
- **middleware/**: セキュリティヘッダーなど
- **dependencies/**: 依存性注入
- **schemas/**: Pydantic入出力スキーマ

### 共通層
- **core/**: 設定管理（config.py）
- **main.py**: アプリケーションエントリーポイント
- **static/**: 静的ファイル（CSS、JavaScript、画像など）
- **templates/**: Jinja2テンプレートファイル

### セッション管理
RDBベースのセッション管理（Redisは使用しない）:
- Fernet暗号化によるセッションデータ保護
- CSRF保護機能
- セッション固定攻撃対策（User-Agent + IPフィンガープリント）
- SESSION_ENCRYPTION_KEY環境変数で暗号化キーを設定

### データベース設定
- **DATABASE_URL**: PostgreSQL接続文字列（優先）
- **POSTGRES_***: 個別設定（後方互換、DATABASE_URL未設定時のみ有効）
- **Supabase対応**: URLに'supabase.co'が含まれる場合、自動検出
- DATABASE_URL未設定時: 警告を出してDB機能無効で続行

### Docker設定
プロジェクトはマルチプロファイルDocker Compose設定を使用:
- **server**: メインFastAPIアプリケーションサービス
- **db**: PostgreSQL 17（ヘルスチェック付き）
- **db-migrator**: Alembicマイグレーション
- **adminer**: データベース管理UI（開発のみ）
- **db-dumper**: データベースバックアップ

`INCLUDE_DB=true`でデータベースサービスを有効化。

## 開発ワークフロー

1. `make env`で.env.exampleから.envファイルを作成
2. .envファイルでデータベースとAPI設定を構成
   - DATABASE_URLを設定（推奨）または個別のPOSTGRES_*変数を設定
   - SESSION_ENCRYPTION_KEYを設定（必須）
3. `make dev:setup`で依存関係をインストール
4. `make up INCLUDE_DB=true`でデータベース付きで起動
5. `make db:migrate`でデータベースマイグレーションを適用
6. コミット前に`make lint`と`make format`を使用
7. `make test`でテストを実行して動作確認

## 主要ファイル

- `app/main.py` - FastAPIアプリケーション設定とミドルウェア
- `app/core/config.py` - 環境設定とPydantic設定クラス
- `app/infrastructure/database/models/base.py` - タイムスタンプMixin付きベースモデル
- `app/infrastructure/database/models/session.py` - セッションモデル
- `app/infrastructure/repositories/session_repository.py` - セッションサービス
- `app/infrastructure/security/encryption.py` - セッション暗号化
- `app/presentation/api/__init__.py` - APIルーター統合

## 典型的な開発タスク

### 新しいAPIエンドポイントを作成
1. `app/infrastructure/database/models/`に新しいモデルファイルを作成
2. `app/presentation/schemas/`に対応するPydanticスキーマを作成
3. `app/infrastructure/repositories/`にリポジトリを作成
4. `app/application/use_cases/`にユースケースを作成（必要に応じて）
5. `app/presentation/api/v1/`にAPIルーターを作成
6. `app/presentation/api/v1/__init__.py`にルーターを登録
7. `make db:revision:create NAME="add_model"`でマイグレーションを作成
8. `make db:migrate`で適用
9. `make test`でテストを実行

### データベースモデルを追加
1. `app/infrastructure/database/models/`に新しいモデルファイルを作成
2. `app/presentation/schemas/`に対応するPydanticスキーマを作成
3. `app/infrastructure/repositories/`にリポジトリを作成
4. `make db:revision:create NAME="add_model"`でマイグレーションを作成
5. `make db:migrate`で適用

### 環境設定を追加
1. `app/core/config.py`の`Settings`クラスに新しいフィールドを追加
2. `.env`ファイルを更新
3. APIエンドポイントで`get_settings()`を使用してアクセス

### ミドルウェアを追加
1. `app/presentation/middleware/`に新しいミドルウェアクラスを作成
2. `app/main.py`でミドルウェアを登録

## テスト

プロジェクトはpytestを使用した包括的なテストスイートを備えています:

### テスト構成
- **tests/conftest.py**: テスト用フィクスチャ（SQLiteインメモリDB、TestClient）
- **tests/integration/**: API統合テスト
- **tests/unit/**: ユニットテスト（セキュリティ、リポジトリなど）

### テスト実行
- `make test`: 全テストを実行
- `make test:cov`: カバレッジレポート付きで実行
- `uv run pytest tests/ -v`: 直接実行

### テスト追加
1. `tests/unit/`または`tests/integration/`に新しいテストファイルを作成
2. pytest規約に従って`test_`プレフィックスを使用
3. `conftest.py`のフィクスチャ（`client`, `db_session`）を活用
4. `make test`で動作確認

## 監視とエラーハンドリング

- Sentry統合によるエラートラッキング
- New Relic APM監視（本番環境）
- 構造化ログ出力
- カスタム例外ハンドリング（`app/domain/exceptions/`）
- ヘルスチェックエンドポイント（`/system/healthcheck/`） 