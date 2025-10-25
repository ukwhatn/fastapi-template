# デプロイメントガイド

このガイドでは、FastAPIアプリケーションのローカル、開発、本番環境へのデプロイ方法を説明します。

## 目次

- [概要](#概要)
- [環境設定](#環境設定)
- [前提条件](#前提条件)
- [ローカル開発](#ローカル開発)
- [開発環境](#開発環境)
- [本番環境](#本番環境)
- [Watchtowerセットアップ](#watchtowerセットアップ)
- [トラブルシューティング](#トラブルシューティング)

## 概要

プロジェクトは3つのデプロイ環境を使用します：

| 環境 | アプリ実行 | データベース | プロキシ | 自動デプロイ |
|------|-----------|-------------|---------|-------------|
| **Local** | uvネイティブ | Docker（オプション） | なし | なし |
| **Dev** | Docker（GHCR.io） | Docker PostgreSQL | Cloudflare Tunnels | Watchtower（develop） |
| **Prod** | Docker（GHCR.io） | 外部（Supabase） | nginx + Cloudflare | Watchtower（latest） |

### 主な機能

- **マルチプラットフォームビルド**: linux/amd64, linux/arm64
- **自動デプロイ**: WatchtowerがGHCR.ioの更新を監視
- **ラベルベース制御**: `watchtower.enable=true`のコンテナのみ更新
- **暗号化シークレット**: SOPS + ageによる安全なシークレット管理
- **SSH不要**: デプロイにSSHは不要

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

自動更新付きDocker開発環境：

```bash
# Dev環境デプロイ
make dev:deploy

# または手動で
./scripts/deploy-dev.sh
```

### Prod

外部データベース使用の本番環境：

```bash
# 本番環境デプロイ
make prod:deploy

# または手動で
./scripts/deploy-prod.sh
```

## 前提条件

### 全環境共通

- Docker & Docker Compose
- Git
- Make

### Localのみ

- uv（Pythonパッケージマネージャー）
- Python 3.13+

### Dev/Prodのみ

- SOPS（[インストール方法](https://github.com/getsops/sops#download)）
- age（[インストール方法](https://github.com/FiloSottile/age#installation)）
- `packages:read`権限付きGitHub Personal Access Token

## ローカル開発

### 初期セットアップ

1. **リポジトリクローン**
   ```bash
   git clone https://github.com/owner/repo.git
   cd repo
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

1. **前提条件インストール**
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

2. **ageキーペア生成**（存在しない場合）
   ```bash
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt

   # 公開鍵（age1xxx...）を保存して.sops.yamlを更新
   cat ~/.config/sops/age/keys.txt | grep "public key:"
   ```

3. **Watchtowerセットアップ**（サーバーごとに1つ）
   ```bash
   ./scripts/setup-watchtower.sh

   # 選択: 1 (dev)
   # Discord/Slack通知URL入力（オプション）
   ```

4. **GitHub認証設定**
   ```bash
   # GitHub Personal Access Tokenを作成:
   # https://github.com/settings/tokens/new
   # 必要な権限: packages:read

   # .env.devに追加:
   echo "GITHUB_USER=your-username" >> .env.dev
   echo "GITHUB_TOKEN=ghp_xxxxx" >> .env.dev
   ```

5. **シークレット暗号化**
   ```bash
   # .sops.yamlを公開鍵で更新
   nano .sops.yaml

   # Dev環境を作成して暗号化
   cp .env.example .env.dev
   nano .env.dev  # Dev設定で編集
   sops -e .env.dev > .env.dev.enc

   # 暗号化ファイルをコミット
   git add .env.dev.enc .sops.yaml
   git commit -m "Add encrypted dev secrets"
   git push
   ```

### デプロイ

```bash
# Devサーバーでリポジトリクローン
git clone https://github.com/owner/repo.git
cd repo

# デプロイ
./scripts/deploy-dev.sh
```

### 自動更新

`develop`ブランチにpushすると：

1. GitHub Actionsがビルドして`develop`タグでGHCR.ioにpush
2. Watchtowerが新しいイメージを検出（10分以内）
3. Watchtowerが`watchtower.enable=true`のコンテナをpull＆再起動
4. Discord/Slackに通知送信
5. ダウンタイム: 10-30秒

### 手動操作

```bash
# ログ表示
docker compose -f compose.dev.yml logs -f

# ステータス確認
docker compose -f compose.dev.yml ps

# Watchtowerログ確認
docker logs watchtower -f

# サービス再起動
docker compose -f compose.dev.yml restart

# サービス停止
docker compose -f compose.dev.yml down
```

## 本番環境

### 初期セットアップ（サーバーごとに1回）

[開発環境 初期セットアップ](#初期セットアップサーバーごとに1回)と同じですが：

1. ステップ4で本番設定を使用
2. Watchtowerセットアップで`2 (prod)`を選択
3. `.env.dev`の代わりに`.env.prod`を使用

### デプロイ

```bash
# 本番サーバーでリポジトリクローン
git clone https://github.com/owner/repo.git
cd repo

# デプロイ（確認プロンプト付き）
./scripts/deploy-prod.sh
```

### 自動更新

`main`ブランチにpushすると：

1. GitHub Actionsがビルドして`latest`タグでGHCR.ioにpush
2. Watchtowerが新しいイメージを検出（10分以内）
3. Watchtowerがコンテナをpull＆再起動
4. Discord/Slackに通知送信
5. ダウンタイム: 10-30秒

### 手動操作

Devと同じですが、`compose.prod.yml`を使用：

```bash
docker compose -f compose.prod.yml logs -f
docker compose -f compose.prod.yml ps
docker compose -f compose.prod.yml restart
docker compose -f compose.prod.yml down
```

## Watchtowerセットアップ

### 概要

- **サーバーごとに1つのWatchtower**（プロジェクトごとではない）
- **ラベルベース制御**: `watchtower.enable=true`のコンテナのみ更新
- **自己更新**: cronによる週1回の自動更新

### 設定

`setup-watchtower.sh`スクリプトが以下を設定：

- ポーリング間隔: 600秒（10分）
- クリーンアップ: 更新後に古いイメージを削除
- 通知: Shoutrrr経由でDiscord/Slack
- Cron: 週1回の自己更新

### ラベル

コンテナはWatchtower制御用にラベル付け：

```yaml
# 自動更新有効
labels:
  - "com.centurylinklabs.watchtower.enable=true"

# 自動更新無効
labels:
  - "com.centurylinklabs.watchtower.enable=false"
```

### 監視

```bash
# Watchtowerログ
docker logs watchtower -f

# Watchtowerステータス
docker ps --filter "name=watchtower"

# 自己更新ログ
sudo cat /var/log/watchtower-update.log
```

## トラブルシューティング

### イメージpullエラー

**症状**: `Error response from daemon: unauthorized`

**解決方法**:
```bash
# GHCR.ioに再ログイン
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin

# トークン権限確認（packages:read必要）
gh auth status
```

### Watchtowerが更新しない

**症状**: 新しいイメージが利用可能だがコンテナが更新されない

**診断**:
```bash
# Watchtowerログ確認
docker logs watchtower -f

# ラベル確認
docker inspect myapp-dev-server | grep watchtower
# 期待値: "com.centurylinklabs.watchtower.enable": "true"

# Watchtower実行中か確認
docker ps --filter "name=watchtower"
```

**解決方法**:
```bash
# Watchtower再起動
docker restart watchtower

# または再作成
./scripts/setup-watchtower.sh
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
docker compose -f compose.dev.yml logs server

# ヘルスステータス確認
docker ps --filter "name=server"

# ヘルスエンドポイントテスト
docker exec myapp-dev-server curl -f http://localhost:80/system/healthcheck/
```

**解決方法**:
```bash
# DATABASE_URLが正しいか確認
docker exec myapp-dev-server env | grep DATABASE

# マイグレーション実行確認
docker compose -f compose.dev.yml logs db-migrator

# サービス再起動
docker compose -f compose.dev.yml restart
```

### Watchtowerが誤ったコンテナを更新

**症状**: 無関係なコンテナが更新された

**解決方法**:

ラベルベース制御では発生しないはずです。確認：

```bash
# Watchtower設定確認
docker inspect watchtower | grep WATCHTOWER_LABEL_ENABLE
# 期待値: "WATCHTOWER_LABEL_ENABLE=true"

# 全コンテナのラベル確認
docker inspect <container-name> | grep watchtower

# ラベル制御付きでWatchtower再作成
docker stop watchtower
docker rm watchtower
./scripts/setup-watchtower.sh
```

### developブランチが本番環境にデプロイされた

**症状**: Dev用コードが本番環境で実行されている

**予防策**:

これは起こりえません。理由：
- `compose.prod.yml` → `latest`タグ（`main`から）
- `compose.dev.yml` → `develop`タグ（`develop`から）
- タグは完全に分離

**復旧方法**:
```bash
# 正しいイメージをpull
docker compose -f compose.prod.yml pull

# 再起動
docker compose -f compose.prod.yml up -d
```

## ベストプラクティス

1. **Dev/Prodでは常に暗号化envファイルを使用**
2. **`.env`や秘密鍵をgitにコミットしない**
3. **更新後はWatchtowerログを監視**
4. **本番デプロイ前にDevでテスト**
5. **age鍵を安全にバックアップ**
6. **GitHubトークンを定期的にローテート**
7. **Watchtower更新ログを週1回確認**

## 参考資料

- [SOPS Documentation](https://github.com/getsops/sops)
- [age Documentation](https://github.com/FiloSottile/age)
- [Watchtower Documentation](https://containrrr.dev/watchtower/)
- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Secrets Management Guide](./secrets-management.md)
