# FastAPI Template

## コマンド
### 環境構築
- `make project:init NAME="プロジェクト名"` - カスタム名で新規プロジェクトを初期化
- `make envs:setup` - 環境変数ファイルをサンプルから作成
- `make dev:setup` - Poetryで依存関係をインストール

### Docker管理
- `make build` - Dockerコンテナをビルド
- `make up` - Dockerコンテナを起動
- `make down` - Dockerコンテナを停止
- `make logs` - コンテナログを表示
- `make reload` - コンテナを再ビルドして再起動
- `make ps` - 実行中のコンテナを表示

### コード品質
- `make lint` - Ruffリンターを実行
- `make lint:fix` - 自動修正を適用しながらRuffリンターを実行
- `make format` - Ruffフォーマッターでコードを整形

### セキュリティ
- `make security:scan` - すべてのセキュリティスキャンを実行
- `make security:scan:code` - Banditによるコードの静的セキュリティ分析
- `make security:scan:sast` - Semgrepによる高度な静的アプリケーションセキュリティテスト

### データベース操作
- `make db:revision:create NAME="メッセージ"` - 新規マイグレーションを作成
- `make db:migrate` - データベースマイグレーションを実行
- `make db:current` - 現在のマイグレーションリビジョンを表示
- `make db:history` - マイグレーション履歴を表示
- `make db:downgrade REV=ターゲット` - 特定のリビジョンにダウングレード
- `make db:dump` - 対話型データベースダンプユーティリティ
- `make db:dump:oneshot` - ワンタイムデータベースダンプを作成
- `make db:dump:list` - 利用可能なデータベースダンプを一覧表示
- `make db:dump:restore FILE=ファイル名` - ダンプからデータベースを復元

### デプロイメント
- `make deploy:prod` - 本番環境へビルドしてデプロイ
