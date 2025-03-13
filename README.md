# FastAPI Template

FastAPIアプリケーションのためのテンプレートリポジトリ。

## 特徴

- FastAPI 0.115.0+
- SQLAlchemy 2.0
- Alembic
- Redisセッション管理
- Docker/Docker Compose
- Poetry
- Ruff
- Sentry
- New Relic

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

1. 環境ファイル設定:
```bash
make envs:setup
```

2. 依存関係インストール:
```bash
make dev:setup
```

3. コンテナ起動:
```bash
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
```

### Docker
```bash
make build       # コンテナビルド
make up          # コンテナ起動
make down        # コンテナ停止
make logs        # ログ表示
make reset       # 環境リセット
```

## 環境設定
- 開発: `compose.dev.yml`
- ステージング: `compose.stg.yml`
- 本番: `compose.prod.yml`
- テスト: `compose.test.yml`