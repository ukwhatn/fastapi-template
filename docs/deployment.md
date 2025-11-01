# Deployment

本プロジェクトのデプロイメント戦略とワークフロー。3環境（Local/Stg/Prod）対応、GitHub Actions自動デプロイ、SOPS暗号化シークレット管理。

## 環境構成

| 環境 | アプリ実行 | データベース | プロキシ | 自動デプロイ | Composeファイル |
|------|-----------|-------------|---------|-------------|----------------|
| **Local** | uv native (hot reload) | Docker (optional) | なし | なし | `compose.local.yml` |
| **Stg** | Docker (GHCR.io) | Docker PostgreSQL | Cloudflare Tunnels | GitHub Actions (develop) | `compose.stg.yml` |
| **Prod** | Docker (GHCR.io) | External (Supabase) | nginx + Cloudflare | GitHub Actions (main) | `compose.prod.yml` |

### デプロイメント機能

- **マルチプラットフォームビルド**: linux/amd64, linux/arm64対応
- **イメージタグ戦略**:
  - `main`ブランチ → `latest`, `main`, `main-sha-xxx`
  - `develop`ブランチ → `develop`, `develop-sha-xxx`
- **自動デプロイ**: GitHub ActionsがSSH経由でサーバーデプロイ
- **Sparse Checkout**: 必要最小限のファイルのみクローン（ディスク使用量削減）
- **暗号化シークレット**: SOPS + ageで安全にGit管理

## Local環境

### 初期セットアップ

```bash
# 依存関係インストール
make dev:setup

# 環境ファイル作成
make env
# .envをローカル設定で編集

# データベース起動
docker compose -f compose.local.yml up -d

# マイグレーション実行
make db:migrate

# アプリケーション起動
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

### 日常のワークフロー

```bash
# サービス起動
docker compose -f compose.local.yml up -d
uv run fastapi dev app/main.py

# サービス停止
docker compose -f compose.local.yml down
```

## Stg環境

### 前提条件

**サーバー側**:
- Docker & Docker Compose
- Git, Make
- SOPS ([インストール](https://github.com/getsops/sops#download))
- age ([インストール](https://github.com/FiloSottile/age#installation))
- SSH サーバー

**GitHub側**:
- Secrets設定（後述）

### 初期セットアップ（1回のみ）

#### 1. ageキーペア生成

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt

# 公開鍵を確認（.sops.yaml更新に使用）
cat ~/.config/sops/age/keys.txt | grep "public key:"
```

#### 2. 暗号化環境ファイル作成（ローカルで）

```bash
# Stg環境設定を作成
cp .env.example .env.stg
nano .env.stg  # Stg設定で編集

# 暗号化
make secrets:encrypt:stg

# Gitにコミット
git add .env.stg.enc .sops.yaml
git commit -m "Add encrypted stg secrets"
git push
```

#### 3. サーバーでセットアップ

```bash
# リポジトリクローン（sparse checkout）
curl -o setup-server.sh https://raw.githubusercontent.com/ukwhatn/fastapi-template/develop/scripts/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh stg

# または手動で：
git clone --filter=blob:none --sparse https://github.com/ukwhatn/fastapi-template.git
cd fastapi-template
git sparse-checkout set compose.stg.yml .env.stg.enc .sops.yaml Makefile newrelic.ini
make secrets:decrypt:stg
ENV=stg make compose:pull
ENV=stg make compose:up
```

#### 4. GitHub Secrets設定

リポジトリ Settings > Secrets and variables > Actions で設定：

| Secret | 内容 |
|--------|------|
| `STG_SSH_HOST` | ステージングサーバーホスト名/IP |
| `STG_SSH_USER` | SSHユーザー名 |
| `STG_SSH_PORT` | SSHポート（デフォルト: 22） |
| `STG_SSH_PRIVATE_KEY` | SSH秘密鍵（`cat ~/.ssh/id_rsa`） |

### 自動デプロイフロー

`develop`ブランチへのpushで以下を自動実行：

1. CI実行（lint, test, type-check）
2. Dockerイメージビルド＆GHCR.ioにpush（`develop`タグ）
3. SSH経由でサーバー接続
4. `git pull origin develop`で最新compose.yml取得
5. `docker compose pull`で最新イメージ取得
6. `docker compose up -d --force-recreate`でコンテナ再起動
7. ヘルスチェック確認（60秒タイムアウト）
8. デプロイ結果をGitHub Actionsに報告

### 手動操作

```bash
# ログ表示
ENV=stg make compose:logs

# ステータス確認
ENV=stg make compose:ps

# サービス再起動
ENV=stg make compose:restart

# サービス停止
ENV=stg make compose:down
```

## Prod環境

### 初期セットアップ（1回のみ）

Stg環境と同じ手順ですが以下が異なります：

1. ステップ2で本番設定を使用（`.env.prod`, `make secrets:encrypt:prod`）
2. ステップ3で `./setup-server.sh prod`を実行
3. GitHub Secretsは`PROD_`プレフィックスを使用
   - `PROD_SSH_HOST`
   - `PROD_SSH_USER`
   - `PROD_SSH_PORT`
   - `PROD_SSH_PRIVATE_KEY`

### 自動デプロイフロー

`main`ブランチへのpushで以下を自動実行：

1. CI実行
2. Dockerイメージビルド＆GHCR.ioにpush（`latest`タグ）
3. SSH経由でサーバーデプロイ
4. ヘルスチェック確認
5. デプロイ結果をGitHub Actionsに報告

### 手動操作

```bash
# ログ表示
ENV=prod make compose:logs

# ステータス確認
ENV=prod make compose:ps

# サービス再起動
ENV=prod make compose:restart

# サービス停止
ENV=prod make compose:down
```

## シークレット管理（SOPS + age）

### 暗号化

```bash
# Stg環境
make secrets:encrypt:stg

# Prod環境
make secrets:encrypt:prod
```

### 復号化

```bash
# Stg環境
make secrets:decrypt:stg

# Prod環境
make secrets:decrypt:prod
```

### 手動操作

```bash
# 暗号化
sops -e .env.stg > .env.stg.enc

# 復号化
sops -d .env.stg.enc > .env

# 暗号化ファイル編集
sops .env.stg.enc
```

**Reference**: 詳細は [Secrets Management Guide](./secrets-management.md) 参照

## マイグレーション管理

### 自動実行

- **起動時自動実行**: アプリケーション起動時（FastAPI lifespan）にマイグレーション自動適用
- **場所**: `app/infrastructure/database/alembic/versions/`
- **安全性**: 失敗時はアプリケーション起動停止（データ破損防止）
- **冪等性**: Alembicが既適用マイグレーションをスキップ（再起動安全）

### 手動操作

```bash
# 新しいマイグレーション作成
make db:revision:create NAME="description"

# マイグレーション適用（手動）
make db:migrate

# ロールバック
make db:downgrade REV=-1

# 現在のリビジョン確認
make db:current

# マイグレーション履歴
make db:history
```

**Note**: 通常は手動実行不要（自動適用されるため）

## トラブルシューティング

### イメージpullエラー

**症状**: `Error response from daemon: unauthorized`

**解決方法**:
```bash
# GHCR.ioに再ログイン
source .env
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin

# トークン権限確認（packages:read必要）
gh auth status
```

### GitHub Actions デプロイ失敗

**症状**: SSH接続エラーまたはpermission denied

**診断**:
```bash
# SSH接続テスト
ssh -i ~/.ssh/id_rsa -p 22 user@host

# GitHub Secrets確認
# Settings > Secrets > Actions
```

**解決方法**:
```bash
# SSH鍵を再生成
ssh-keygen -t ed25519 -C "github-actions"

# 公開鍵をサーバーに追加
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host

# 秘密鍵をGitHub Secretsに追加
cat ~/.ssh/id_ed25519 | pbcopy  # macOS
# GitHub Settings > Secrets > STG_SSH_PRIVATE_KEY に貼り付け
```

### SOPS復号化エラー

**症状**: `failed to get the data key required to decrypt the SOPS file`

**解決方法**:
```bash
# age鍵の存在確認
ls -la ~/.config/sops/age/keys.txt

# パーミッション修正
chmod 600 ~/.config/sops/age/keys.txt

# 復号化テスト
sops -d .env.stg.enc
```

### ヘルスチェックタイムアウト

**症状**: コンテナは起動するがヘルスチェックに失敗

**診断**:
```bash
# コンテナログ確認
ENV=stg make compose:logs

# ヘルスステータス確認
ENV=stg make compose:ps

# ヘルスエンドポイントテスト
docker exec fastapi-template-server-stg curl -f http://localhost:80/api/system/healthcheck/
```

**解決方法**:
```bash
# DATABASE_URLが正しいか確認
docker exec fastapi-template-server-stg env | grep DATABASE

# サービス再起動
ENV=stg make compose:restart
```

### git pull失敗（サーバー側）

**症状**: GitHub Actionsデプロイ時に`git pull`でコンフリクト

**解決方法**:
```bash
# サーバーでローカル変更を破棄
cd fastapi-template
git reset --hard origin/develop  # または origin/main

# 再デプロイ
git push origin develop --force-with-lease
```

## ロールバック

### 方法1: Gitでrevert（推奨）

```bash
# 問題のあるコミットをrevert
git revert <commit-hash>
git push origin develop  # または main

# GitHub Actionsが自動で前のバージョンをデプロイ
```

### 方法2: 手動ロールバック

```bash
# サーバーにSSH
ssh user@host
cd fastapi-template

# 特定のコミットにチェックアウト
git checkout <previous-commit-hash>

# 再起動
ENV=stg docker compose pull
ENV=stg docker compose up -d --force-recreate

# 確認後、元に戻す
git checkout develop  # または main
```

## ベストプラクティス

1. **暗号化環境ファイルを必ず使用** - Stg/Prodでは常にSOPS暗号化
2. **平文シークレットをGitに含めない** - `.env`や秘密鍵を`.gitignore`
3. **デプロイ後はログ確認** - GitHub Actionsログとサーバーログ
4. **本番前にStgでテスト** - 本番デプロイ前にステージング環境で検証
5. **age鍵を安全にバックアップ** - 紛失するとデプロイ不可
6. **GitHubトークンを定期的にローテート** - セキュリティ強化
7. **GitHub Actions専用SSH鍵を使用** - 個人用鍵と分離
8. **Sparse Checkoutで必要最小限** - ディスク使用量削減
9. **ダウンタイム考慮** - デプロイ時10-30秒のダウンタイム発生
10. **ブランチ分離** - develop/mainで異なるタグとサーバー使用

## デプロイメント詳細

### ダウンタイム

- **期間**: 10-30秒（コンテナ再起動時）
- **理由**: `--force-recreate`によるコンテナ再作成
- **軽減策**: ブルーグリーンデプロイメント（将来実装）

### ブランチ戦略

- **develop → Stg環境**: ステージング・テスト用
- **main → Prod環境**: 本番用
- **PRフロー**: feature → develop → main

### モニタリング

- **GitHub Actionsログ**: デプロイプロセス確認
- **サーバーログ**: `ENV={stg|prod} make compose:logs`
- **Sentry**: エラートラッキング（本番）
- **New Relic**: APMモニタリング（本番）

## 参考資料

- [Secrets Management Guide](./secrets-management.md) - SOPS + age詳細ガイド
- [Architecture](./architecture.md) - Clean Architecture実装詳細
- [SOPS Documentation](https://github.com/getsops/sops)
- [age Documentation](https://github.com/FiloSottile/age)
- [GitHub Actions SSH Action](https://github.com/appleboy/ssh-action)
- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
