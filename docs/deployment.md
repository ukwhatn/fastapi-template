# デプロイメントガイド

このガイドでは、FastAPIアプリケーションのローカル、開発、本番環境へのデプロイ方法を説明します。

## 目次

- [概要](#概要)
- [環境設定](#環境設定)
- [前提条件](#前提条件)
- [ローカル開発](#ローカル開発)
- [開発環境](#開発環境)
- [本番環境](#本番環境)
- [トラブルシューティング](#トラブルシューティング)

## 概要

プロジェクトは3つのデプロイ環境を使用します：

| 環境 | アプリ実行 | データベース | プロキシ | 自動デプロイ |
|------|-----------|-------------|---------|-------------|
| **Local** | uvネイティブ | Docker（オプション） | なし | なし |
| **Dev** | Docker（GHCR.io） | Docker PostgreSQL | Cloudflare Tunnels | GitHub Actions（develop） |
| **Prod** | Docker（GHCR.io） | 外部（Supabase） | nginx + Cloudflare | GitHub Actions（main） |

### 主な機能

- **マルチプラットフォームビルド**: linux/amd64, linux/arm64
- **自動デプロイ**: GitHub ActionsがSSH経由でサーバーにデプロイ
- **Sparse Checkout**: 必要最小限のファイルのみクローン
- **暗号化シークレット**: SOPS + ageによる安全なシークレット管理
- **SSH不要（開発者側）**: デプロイはGitHub Actionsが自動実行

## 環境設定

### Local

ホットリロード付きローカル開発：

```bash
# データベースサービス起動
docker compose -f compose.local.yml up -d

# アプリをuvでネイティブ実行
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

### Dev

GitHub Actions自動デプロイ：

```bash
# 開発サーバーで初回セットアップ（1回のみ）
./scripts/setup-server.sh dev

# 以降はdevelopブランチへのpushで自動デプロイ
git push origin develop
```

### Prod

GitHub Actions自動デプロイ：

```bash
# 本番サーバーで初回セットアップ（1回のみ）
./scripts/setup-server.sh prod

# 以降はmainブランチへのpushで自動デプロイ
git push origin main
```

## 前提条件

### 全環境共通

- Docker & Docker Compose
- Git
- Make

### Localのみ

- uv（Pythonパッケージマネージャー）
- Python 3.13+

### Dev/Prodのみ（サーバー側）

- SOPS（[インストール方法](https://github.com/getsops/sops#download)）
- age（[インストール方法](https://github.com/FiloSottile/age#installation)）
- SSH サーバー（GitHub Actionsからの接続用）

### Dev/Prod（GitHub側）

- GitHub Secrets設定（後述）

## ローカル開発

### 初期セットアップ

1. **リポジトリクローン**
   ```bash
   git clone https://github.com/ukwhatn/fastapi-template.git
   cd fastapi-template
   ```

2. **依存関係インストール**
   ```bash
   make dev:setup
   ```

3. **環境ファイル作成**
   ```bash
   make env
   # .envをローカル設定で編集
   ```

4. **データベースサービス起動**
   ```bash
   docker compose -f compose.local.yml up -d
   ```

5. **マイグレーション実行**
   ```bash
   make db:migrate
   ```

6. **アプリケーション起動**
   ```bash
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

## 開発環境

### 初期セットアップ（サーバーごとに1回）

#### 1. 前提条件インストール

```bash
# SOPSインストール
curl -LO https://github.com/getsops/sops/releases/latest/download/sops-latest.linux.amd64
sudo mv sops-latest.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

# ageインストール
sudo apt install age  # Ubuntu/Debian
# または
brew install age  # macOS
```

#### 2. ageキーペア生成（存在しない場合）

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt

# 公開鍵（age1xxx...）を保存して.sops.yamlを更新
cat ~/.config/sops/age/keys.txt | grep "public key:"
```

#### 3. 暗号化ファイル作成（ローカルで）

```bash
# Dev環境設定を作成
cp .env.example .env.dev
nano .env.dev  # Dev設定で編集

# 暗号化
sops -e .env.dev > .env.dev.enc

# Gitにコミット
git add .env.dev.enc .sops.yaml
git commit -m "Add encrypted dev secrets"
git push
```

#### 4. サーバーで初回セットアップ

```bash
# リポジトリクローン（sparse checkout）
curl -o setup-server.sh https://raw.githubusercontent.com/ukwhatn/fastapi-template/develop/scripts/setup-server.sh
chmod +x setup-server.sh
./setup-server.sh dev

# または手動で：
git clone --filter=blob:none --sparse https://github.com/ukwhatn/fastapi-template.git
cd fastapi-template
git sparse-checkout set compose.dev.yml .env.dev.enc .sops.yaml Makefile newrelic.ini
sops -d .env.dev.enc > .env
# .envを確認して
ENV=dev make compose:pull
ENV=dev make compose:up
```

#### 5. GitHub Secrets設定

GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定：

- `DEV_SSH_HOST`: 開発サーバーのホスト名またはIP
- `DEV_SSH_USER`: SSHユーザー名
- `DEV_SSH_PORT`: SSHポート（デフォルト: 22）
- `DEV_SSH_PRIVATE_KEY`: SSH秘密鍵（`cat ~/.ssh/id_rsa`）

### 自動デプロイ

`develop` ブランチにpushすると：

1. GitHub Actions CI実行（lint, test等）
2. Dockerイメージビルド＆GHCR.ioにpush（`develop`タグ）
3. SSH経由でサーバー接続
4. `git pull origin develop` で最新のcompose.yml等を取得
5. `docker compose pull` で最新イメージ取得
6. `docker compose up -d --force-recreate` でコンテナ再起動
7. ヘルスチェック確認（60秒タイムアウト）
8. 成功/失敗をGitHub Actionsに報告

### 手動操作

```bash
# ログ表示
ENV=dev make compose:logs

# ステータス確認
ENV=dev make compose:ps

# サービス再起動
ENV=dev make compose:restart

# サービス停止
ENV=dev make compose:down
```

## 本番環境

### 初期セットアップ（サーバーごとに1回）

[開発環境 初期セットアップ](#初期セットアップサーバーごとに1回)と同じですが：

1. ステップ3で本番設定を使用（`.env.prod`）
2. ステップ4で `./setup-server.sh prod` を実行
3. GitHub Secretsは `PROD_` プレフィックスを使用

### 自動デプロイ

`main` ブランチにpushすると：

1. GitHub Actions CI実行
2. Dockerイメージビルド＆GHCR.ioにpush（`latest`タグ）
3. SSH経由でサーバーにデプロイ
4. ヘルスチェック確認
5. 成功/失敗をGitHub Actionsに報告

### 手動操作

Devと同じですが、`compose.prod.yml`を使用：

```bash
ENV=prod make compose:logs
ENV=prod make compose:ps
ENV=prod make compose:restart
ENV=prod make compose:down
```

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
# SSH接続テスト（ローカルから）
ssh -i ~/.ssh/id_rsa -p 22 user@host

# GitHub Secrets確認
# Settings > Secrets > Actions で設定を確認
```

**解決方法**:
```bash
# SSH鍵を再生成
ssh-keygen -t ed25519 -C "github-actions"

# 公開鍵をサーバーに追加
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host

# 秘密鍵をGitHub Secretsに追加
cat ~/.ssh/id_ed25519 | pbcopy  # macOS
# GitHub Settings > Secrets > DEV_SSH_PRIVATE_KEY に貼り付け
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
sops -d .env.dev.enc
```

### ヘルスチェックタイムアウト

**症状**: コンテナは起動するがヘルスチェックに失敗

**診断**:
```bash
# コンテナログ確認
ENV=dev make compose:logs

# ヘルスステータス確認
ENV=dev make compose:ps

# ヘルスエンドポイントテスト
docker exec fastapi-template-server-dev curl -f http://localhost:80/system/healthcheck/
```

**解決方法**:
```bash
# DATABASE_URLが正しいか確認
docker exec fastapi-template-server-dev env | grep DATABASE

# サービス再起動
ENV=dev make compose:restart
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

## ベストプラクティス

1. **Dev/Prodでは常に暗号化envファイルを使用**
2. **`.env`や秘密鍵をgitにコミットしない**
3. **デプロイ後はGitHub Actionsログを確認**
4. **本番デプロイ前にDevでテスト**
5. **age鍵を安全にバックアップ**
6. **GitHubトークンを定期的にローテート**
7. **SSH鍵は専用のものを使用（GitHub Actions専用）**

## ロールバック手順

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
ENV=dev docker compose pull
ENV=dev docker compose up -d --force-recreate

# 確認後、元に戻す
git checkout develop  # または main
```

## 参考資料

- [SOPS Documentation](https://github.com/getsops/sops)
- [age Documentation](https://github.com/FiloSottile/age)
- [GitHub Actions SSH Action](https://github.com/appleboy/ssh-action)
- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Secrets Management Guide](./secrets-management.md)
