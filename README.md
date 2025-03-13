# FastAPI Template

FastAPIアプリケーションのためのテンプレートリポジトリ。

## 特徴

- FastAPI 0.115.0+
- SQLAlchemy 2.0
- Alembic マイグレーション
- Redisセッション管理
- Docker/Docker Compose
- Poetry 依存関係管理
- S3 データベースバックアップ
- Ruff リンターとフォーマッター
- Sentry エラー監視
- New Relic パフォーマンス監視

## プロジェクト構造

```
├── app/                 # アプリケーションコード
│   ├── api/             # API実装
│   │   ├── deps/        # 依存性注入
│   │   ├── v1/          # APIバージョン1
│   │   └── system/      # システムAPI
│   ├── core/            # コアモジュール
│   ├── db/              # データベース関連
│   │   ├── crud/        # CRUD操作
│   │   ├── models/      # モデル
│   │   └── schemas/     # スキーマ
│   └── utils/           # ユーティリティ
├── migrations/          # マイグレーション
├── tests/               # テスト
└── docker/              # Dockerファイル
```

## 始め方

### 新規プロジェクトの作成

このテンプレートを元に新しいプロジェクトを作成する場合：

```bash
# アプリケーション名を変更し、環境ファイルを設定
make project:init NEW_NAME="my-app-name"

# 依存関係をインストール
make dev:setup
```

### 既存プロジェクトの利用

```bash
# 環境ファイル設定
make envs:setup

# 依存関係インストール
make dev:setup

# コンテナ起動
make up
```

アプリケーション: http://localhost:8000
API ドキュメント: http://localhost:8000/docs

## コマンド一覧

### コード品質
```bash
make lint        # リント実行
make lint:fix    # リント自動修正
make format      # フォーマット実行
```

### データベース
```bash
make db:revision:create NAME="変更内容"  # マイグレーション作成
make db:migrate                        # マイグレーション実行
make db:dump                           # データベースバックアップ (開発環境)
```

### Docker
```bash
make build       # コンテナビルド
make up          # コンテナ起動
make down        # コンテナ停止
make logs        # ログ表示
make reset       # 環境リセット
```

### プロジェクト管理
```bash
make app:rename NEW_NAME="my-app-name"  # アプリケーション名を変更
make project:init NEW_NAME="my-app-name" # 新規プロジェクト初期化
```

## 環境設定
- 開発: `compose.dev.yml`
- ステージング: `compose.stg.yml`
- 本番: `compose.prod.yml`
- テスト: `compose.test.yml`

## 環境変数ファイル
- `envs/db.env`: データベース接続設定
- `envs/server.env`: サーバー設定
- `envs/sentry.env`: Sentry設定
- `envs/aws-s3.env`: S3バックアップ設定

## データベースバックアップ
本番環境では、`db-dumper`サービスが自動的に毎日指定された時間にデータベースバックアップを実行し、
AWS S3にアップロードします。以下の環境変数で設定を変更できます：

- `BACKUP_HOUR`: バックアップ実行時間（デフォルト: 3）
- `BACKUP_MINUTE`: バックアップ実行分（デフォルト: 0）
- `RETENTION_DAYS`: バックアップ保持日数（デフォルト: 7）
- `DUMPER_MODE`: 実行モード（scheduled: 定期実行、interactive: 対話モード）

開発環境でバックアップ機能を使用するには、`compose.dev.yml`の`db-dumper`サービスのコメントを解除してください。