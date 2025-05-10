# FastAPI Template

## 目次
- [環境構築](#環境構築)
- [Docker管理](#docker管理)
- [コード品質](#コード品質)
- [セキュリティ](#セキュリティ)
- [リソース生成](#リソース生成)
  - [リソース生成の詳細な手順](#リソース生成の詳細な手順)
- [データベース操作](#データベース操作)
- [テンプレート更新](#テンプレート更新)
- [デプロイメント](#デプロイメント)

## コマンド
### 環境構築
- `make project:init NAME="プロジェクト名"` - カスタム名で新規プロジェクトを初期化
- `make envs:setup` - 環境変数ファイルをサンプルから作成
- `make dev:setup` - Poetryで依存関係をインストール

#### 環境構築の詳細

##### プロジェクトの初期化

このテンプレートを使用して新しいプロジェクトを開始するには:

```bash
make project:init NAME="あなたのプロジェクト名"
```

このコマンドは、プロジェクト名を指定された名前に変更し、新しいGitブランチ（develop）を作成します。

##### 環境変数の設定

必要な環境変数ファイルをサンプルから作成します:

```bash
make envs:setup
```

このコマンドは、以下の環境変数ファイルを作成します:
- `envs/server.env` - サーバー設定
- `envs/db.env` - データベース設定
- `envs/sentry.env` - Sentry設定（エラー監視）
- `envs/aws-s3.env` - AWS S3設定（ストレージ）

作成後、各ファイルを編集して適切な値を設定してください。

##### 開発環境のセットアップ

開発に必要な依存関係をインストールします:

```bash
make dev:setup
```

このコマンドは、Poetryを使用して`pyproject.toml`で定義されたすべての依存関係をインストールします。

##### Poetry管理コマンド

Poetryを使用してパッケージを管理するための追加コマンド:

```bash
make poetry:add group=dev packages="pytest pytest-cov"  # 開発用パッケージを追加
make poetry:update group=dev                           # 開発用パッケージを更新
make poetry:lock                                       # 依存関係をロック
```

### Docker管理
- `make build` - Dockerコンテナをビルド
- `make up` - Dockerコンテナを起動
- `make down` - Dockerコンテナを停止
- `make logs` - コンテナログを表示
- `make reload` - コンテナを再ビルドして再起動
- `make ps` - 実行中のコンテナを表示

#### Docker管理の詳細

このプロジェクトはDockerを使用して開発環境と本番環境を管理します。異なる環境用に複数のComposeファイルが用意されています。

##### 環境の選択

デフォルトでは開発環境（`compose.dev.yml`）が使用されます。異なる環境を指定するには、`ENV`変数を使用します:

```bash
make up ENV=prod  # 本番環境
make up ENV=stg   # ステージング環境
make up ENV=test  # テスト環境
```

##### コンテナの構築と起動

コンテナをビルドして起動します:

```bash
make build  # コンテナをビルド
make up     # コンテナを起動
```

一度に両方の操作を行うこともできます（`up`コマンドは自動的にビルドも行います）:

```bash
make up
```

##### コンテナの停止と再起動

コンテナを停止します:

```bash
make down
```

コンテナを再ビルドして再起動します:

```bash
make reload
```

##### ログの表示

コンテナのログを表示します:

```bash
make logs      # ログをリアルタイムで表示（フォロー）
make logs:once # ログを一度だけ表示
```

##### 実行中のコンテナの確認

実行中のコンテナを一覧表示します:

```bash
make ps
```

##### コンテナの完全リセット

コンテナ、ボリューム、ネットワーク、イメージを完全に削除します:

```bash
make reset
```

> **注意**: `reset`コマンドはすべてのデータを削除します。必要なデータはバックアップしてください。

### コード品質
- `make lint` - Ruffリンターを実行
- `make lint:fix` - 自動修正を適用しながらRuffリンターを実行
- `make format` - Ruffフォーマッターでコードを整形

#### コード品質の詳細

##### リンターの実行

コードの問題を検出するためにRuffリンターを実行します:

```bash
make lint
```

自動修正可能な問題を修正しながらリンターを実行します:

```bash
make lint:fix
```

##### コードフォーマット

コードを一貫したスタイルでフォーマットします:

```bash
make format
```

このコマンドは、プロジェクト全体のPythonコードをRuffフォーマッターを使用して整形します。

### セキュリティ
- `make security:scan` - すべてのセキュリティスキャンを実行
- `make security:scan:code` - Banditによるコードの静的セキュリティ分析
- `make security:scan:sast` - Semgrepによる高度な静的アプリケーションセキュリティテスト

#### セキュリティの詳細

##### セキュリティスキャン

コードのセキュリティ問題を検出するために複数のスキャンを実行します:

```bash
make security:scan  # すべてのセキュリティスキャンを実行
```

個別のスキャンを実行することもできます:

```bash
make security:scan:code  # Banditによる静的セキュリティ分析
make security:scan:sast  # Semgrepによる静的アプリケーションセキュリティテスト
```

##### セキュリティベストプラクティス

このプロジェクトでは、以下のセキュリティベストプラクティスを採用しています:
- 環境変数を使用した機密情報の管理
- 適切な認証と認可の実装
- 入力検証とサニタイズ
- SQLインジェクション対策
- XSS対策

### リソース生成
- `make model:generate NAME=resource_name` - モデル、CRUD、スキーマファイルを生成（例: `make model:generate NAME=blog_post`）
- `make router:generate NAME=resource_name` - APIルーターファイルを生成（例: `make router:generate NAME=blog_post`）
- `make resource:generate NAME=resource_name` - 上記の両方を一度に生成（非推奨）

#### リソース生成の詳細な手順

##### 概要
リソース生成機能は、新しいAPIエンドポイントとデータモデルを迅速に作成するためのものです。テンプレートファイルを基にして、必要なファイルを自動生成します。

##### 生成されるファイル
1. **モデル生成（`make model:generate`）**:
   - データベースモデル: `app/db/models/{resource_name}.py`
   - CRUDオペレーション: `app/db/crud/{resource_name}.py`
   - Pydanticスキーマ: `app/db/schemas/{resource_name}.py`

2. **ルーター生成（`make router:generate`）**:
   - APIエンドポイント: `app/api/v1/{resource_name}s.py`

##### 使用方法

**ステップ1: モデルの生成**

```bash
make model:generate NAME=blog_post
```

このコマンドは以下のファイルを生成します:
- `app/db/models/blog_post.py` - SQLAlchemyモデル定義
- `app/db/crud/blog_post.py` - CRUD操作用のクラス
- `app/db/schemas/blog_post.py` - Pydanticスキーマ定義

生成されたファイルは必要に応じてカスタマイズできます。例えば、モデルに追加のフィールドを定義したり、CRUDクラスに特別なメソッドを追加したりできます。

**ステップ2: ルーターの生成**

```bash
make router:generate NAME=blog_post
```

このコマンドは以下のファイルを生成します:
- `app/api/v1/blog_posts.py` - APIエンドポイント定義

**ステップ3: ルーターの登録**

生成されたルーターを使用するには、`app/api/v1/__init__.py`ファイルに登録する必要があります:

```python
from api.v1 import blog_posts

router.include_router(
    blog_posts.router,
    prefix="/blog_posts",
    tags=["BlogPosts"]
)
```

**ステップ4: マイグレーションの作成と実行**

新しいモデルをデータベースに反映するには、マイグレーションを作成して実行します:

```bash
make db:revision:create NAME="Add blog post model"
make db:migrate
```

##### 実際の使用例

ブログ投稿機能を追加する完全な例:

1. モデルとスキーマを生成:
   ```bash
   make model:generate NAME=blog_post
   ```

2. 必要に応じてモデルをカスタマイズ:
   ```python
   # app/db/models/blog_post.py を編集
   class BlogPost(BaseModel):
       __tablename__ = "blog_posts"

       title: Mapped[str] = mapped_column(String(200), index=True)
       content: Mapped[str] = mapped_column(Text)
       published: Mapped[bool] = mapped_column(default=False)
       author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
   ```

3. APIルーターを生成:
   ```bash
   make router:generate NAME=blog_post
   ```

4. ルーターを登録:
   ```python
   # app/api/v1/__init__.py を編集
   from api.v1 import blog_posts

   router.include_router(
       blog_posts.router,
       prefix="/blog_posts",
       tags=["BlogPosts"]
   )
   ```

5. マイグレーションを作成して実行:
   ```bash
   make db:revision:create NAME="Add blog post model"
   make db:migrate
   ```

これで、`/api/v1/blog_posts`エンドポイントが利用可能になり、ブログ投稿のCRUD操作ができるようになります。

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

#### データベース操作の詳細

##### マイグレーション管理

データベースのスキーマ変更はマイグレーションを通じて管理されます。このプロジェクトではAlembicを使用しています。

**マイグレーションの作成**

モデルを変更した後、新しいマイグレーションを作成します:

```bash
make db:revision:create NAME="Add user email column"
```

このコマンドは、`versions`ディレクトリに新しいマイグレーションファイルを作成します。

**マイグレーションの適用**

作成したマイグレーションをデータベースに適用します:

```bash
make db:migrate
```

**マイグレーションの状態確認**

現在のマイグレーション状態を確認します:

```bash
make db:current  # 現在のリビジョンを表示
make db:history  # マイグレーション履歴を表示
```

**マイグレーションのロールバック**

特定のリビジョンにダウングレードします:

```bash
make db:downgrade REV=前のリビジョンID
```

##### データベースダンプと復元

**対話型ダンプユーティリティ**

対話型のデータベースダンプユーティリティを起動します:

```bash
make db:dump
```

このコマンドは、ダンプの作成、一覧表示、復元などのオプションを提供するインタラクティブなインターフェースを表示します。

**ワンタイムダンプの作成**

現在のデータベース状態のスナップショットを作成します:

```bash
make db:dump:oneshot
```

このコマンドは、タイムスタンプ付きのダンプファイルを作成します。

**ダンプの一覧表示**

利用可能なデータベースダンプを一覧表示します:

```bash
make db:dump:list
```

**ダンプからの復元**

特定のダンプファイルからデータベースを復元します:

```bash
make db:dump:restore FILE=dump_20230101_120000.sql
```

> **注意**: 復元操作は現在のデータベースの内容を上書きします。重要なデータがある場合は、事前にバックアップを作成してください。

### テンプレート更新
- `make template:list` - テンプレートの最新コミット一覧を表示
- `make template:apply` - 特定のコミットの変更を適用
- `make template:apply:range` - 指定範囲のコミットの変更を適用
- `make template:apply:force` - 特定のコミットの変更を強制的に適用

#### テンプレート更新の詳細

このプロジェクトは、元のテンプレートリポジトリからの更新を取り込むための機能を提供しています。これにより、テンプレートの改善やバグ修正を既存のプロジェクトに簡単に適用できます。

##### テンプレートの最新変更を確認

テンプレートリポジトリの最新コミット一覧を表示します:

```bash
make template:list
```

このコマンドは、元のテンプレートリポジトリの最新コミットを10件表示します。

##### 特定のコミットを適用

テンプレートの特定のコミットの変更を現在のプロジェクトに適用します:

```bash
make template:apply
```

このコマンドを実行すると、適用したいコミットのハッシュを入力するよう求められます。複数のコミットを適用する場合は、スペースで区切って入力します。

##### コミット範囲を適用

テンプレートの特定の範囲のコミットを適用します:

```bash
make template:apply:range
```

このコマンドを実行すると、開始コミットと終了コミットのハッシュを入力するよう求められます。

##### 強制的に変更を適用

コンフリクトを無視して、テンプレートの変更を強制的に適用します:

```bash
make template:apply:force
```

このコマンドは、指定したコミットの状態を現在のプロジェクトに強制的に適用します。ローカルの変更が上書きされる可能性があるため、注意して使用してください。

> **注意**: テンプレート更新を適用する前に、ローカルの変更をコミットしておくことをお勧めします。コンフリクトが発生した場合は、手動で解決する必要があります。

### デプロイメント
- `make deploy:prod` - 本番環境へビルドしてデプロイ

#### デプロイメントの詳細

##### 本番環境へのデプロイ

本番環境用のコンテナをビルドしてデプロイします:

```bash
make deploy:prod
```

このコマンドは以下の操作を行います:
1. 本番環境用の設定（`compose.prod.yml`）を使用してコンテナをビルド
2. 既存のコンテナを停止
3. 新しいコンテナを起動

##### 本番環境の設定

本番環境用の設定は`compose.prod.yml`ファイルで定義されています。このファイルには、以下のような本番環境固有の設定が含まれています:
- 最適化されたビルド設定
- 適切なネットワーク構成
- セキュリティ強化オプション
- スケーリング設定

本番環境にデプロイする前に、以下の点を確認してください:
1. すべての環境変数が適切に設定されていること
2. データベースのバックアップが作成されていること
3. セキュリティスキャンが実行され、問題がないこと

```bash
make security:scan  # デプロイ前にセキュリティスキャンを実行
```
