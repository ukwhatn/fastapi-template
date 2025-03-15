# FastAPI テンプレートリファレンス

## プロジェクト概要
このリポジトリは、FastAPIを使用したWeb APIを作成するためのテンプレートで、以下の機能を提供します:
- バージョニング対応のモジュラーAPIルーター構造
- SQLAlchemy ORMによるPostgreSQLデータベース連携
- キャッシュとセッション管理のためのRedis
- Dockerベースの開発ワークフロー
- 包括的なエラーハンドリングと監視
- データベースのマイグレーションとバックアップツール

## コマンド
### 環境構築
- `make project:init NAME="プロジェクト名"` - カスタム名で新規プロジェクトを初期化
- `make envs:setup` - 環境変数ファイルをサンプルから作成
- `make dev:setup` - Poetryで依存関係をインストール

### 開発ワークフロー
- `make build` / `make up` / `make down` - Dockerコンテナ管理
- `make reload` - コンテナを再ビルドして再起動
- `make logs` - コンテナログを表示

### コード品質
- `make lint` - Ruffリンターを実行
- `make lint:fix` - 自動修正を適用しながらRuffリンターを実行
- `make format` - Ruffフォーマッターでコードを整形
- `make security:scan` - Banditとsemgrepによるセキュリティスキャン

### データベース操作
- `make db:revision:create NAME="メッセージ"` - 新規マイグレーションを作成
- `make db:migrate` - データベースマイグレーションを実行
- `make db:dump` - データベースバックアップ操作
- `make db:dump:restore FILE=ファイル名` - ダンプからデータベースを復元

## コードスタイル
- Python 3.10+ とFastAPIフレームワーク
- モジュラーなルーター構造 (/app/api/{version}/{module})
- 変数/関数はスネークケース、クラスはパスカルケース
- すべての関数と引数に型アノテーション必須
- SQLAlchemy 2.0スタイルの型ヒント (Mapped[type])
- インポート順序: 1)標準ライブラリ 2)サードパーティ 3)ローカルモジュール
- リクエスト/レスポンスはPydanticモデルで検証
- エラーは明示的に捕捉し、適切なHTTPステータスコードを返す
- Sentryを使用した包括的なロギングと例外トラッキング
- 環境変数はcore.config.Settingsで中央管理