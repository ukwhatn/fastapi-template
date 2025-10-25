# シークレット管理ガイド

このガイドでは、SOPS + ageを使用した安全なシークレット管理方法を説明します。

## 目次

- [概要](#概要)
- [SOPS + ageとは](#sops--ageとは)
- [セットアップ](#セットアップ)
- [基本的な使い方](#基本的な使い方)
- [ワークフロー](#ワークフロー)
- [ベストプラクティス](#ベストプラクティス)
- [トラブルシューティング](#トラブルシューティング)

## 概要

### なぜSOPS + ageを使うのか

| 要件 | 解決方法 |
|-----|---------|
| シークレットをGitで管理したい | ✅ 暗号化ファイルを安全にコミット可能 |
| チーム間でシークレットを共有したい | ✅ 複数の公開鍵で暗号化可能 |
| 変更履歴を追跡したい | ✅ Git履歴で監査可能 |
| CI/CDで自動復号化したい | ✅ 環境変数経由で自動化 |
| コストを抑えたい | ✅ 完全無料（$0） |

### 代替案との比較

| ツール | コスト | Git管理 | 学習コスト | 推奨度 |
|-------|-------|---------|-----------|--------|
| **SOPS + age** | 無料 | ✅ | 低 | ⭐⭐⭐⭐⭐ |
| GPG | 無料 | ✅ | 高 | ⭐⭐⭐ |
| HashiCorp Vault | 有料 | ❌ | 高 | ⭐⭐ |
| AWS Secrets Manager | 有料 | ❌ | 中 | ⭐⭐⭐ |
| Docker Secrets | 無料 | ❌ | 中 | ⭐⭐ |

## SOPS + ageとは

### SOPS (Secrets OPerationS)

Mozillaが開発したシークレット暗号化ツール。JSON、YAML、ENV、INI、BINARYファイルを暗号化できます。

- GitHub: https://github.com/getsops/sops
- 特徴: ファイル構造を保持、差分が見やすい、複数の暗号化バックエンド対応

### age

シンプルで安全なファイル暗号化ツール。GPGの代替として設計されました。

- GitHub: https://github.com/FiloSottile/age
- 特徴: シンプルなAPI、小さな鍵サイズ、高速

## セットアップ

### 1. ツールのインストール

#### SOPS

```bash
# Linux (amd64)
curl -LO https://github.com/getsops/sops/releases/latest/download/sops-latest.linux.amd64
sudo mv sops-latest.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

# macOS
brew install sops

# 確認
sops --version
```

#### age

```bash
# Ubuntu/Debian
sudo apt install age

# macOS
brew install age

# 確認
age --version
```

### 2. age鍵ペアの生成

```bash
# 鍵ディレクトリ作成
mkdir -p ~/.config/sops/age

# 鍵ペア生成
age-keygen -o ~/.config/sops/age/keys.txt

# 出力例:
# Public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# （この公開鍵を.sops.yamlに設定）
```

**重要**:
- `keys.txt`には秘密鍵が含まれます
- **絶対にGitにコミットしないでください**
- 安全な場所にバックアップしてください

### 3. .sops.yaml設定

プロジェクトルートに`.sops.yaml`を作成：

```yaml
creation_rules:
  # Dev環境用
  - path_regex: \.env\.dev(\.enc)?$
    age: >-
      age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

  # Prod環境用
  - path_regex: \.env\.prod(\.enc)?$
    age: >-
      age1yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

  # 複数の公開鍵（チーム共有）
  - path_regex: \.env\.shared(\.enc)?$
    age: >-
      age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
      age1zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
```

**ポイント**:
- `age1xxx...`を実際の公開鍵に置き換える
- 環境ごとに異なる鍵を使用可能
- カンマ区切りで複数の公開鍵を指定可能

### 4. 公開鍵の確認

```bash
# 公開鍵を表示
cat ~/.config/sops/age/keys.txt | grep "public key:"

# または
age-keygen -y ~/.config/sops/age/keys.txt
```

## 基本的な使い方

### 暗号化

```bash
# 新規ファイルを暗号化
cp .env.example .env.dev
nano .env.dev  # 編集
sops -e .env.dev > .env.dev.enc

# インプレース暗号化（元ファイル削除）
sops -e -i .env.dev
```

### 復号化

```bash
# 標準出力に復号化
sops -d .env.dev.enc

# ファイルに復号化
sops -d .env.dev.enc > .env

# インプレース復号化
sops -d -i .env.dev.enc
```

### 編集

```bash
# 暗号化ファイルを直接編集（推奨）
sops .env.dev.enc

# 保存すると自動的に再暗号化
```

### キー情報確認

```bash
# ファイルの暗号化情報を表示
sops -d .env.dev.enc | tail -20

# または
sops --decrypt --extract '["sops"]' .env.dev.enc
```

## ワークフロー

### 開発者Aがシークレットを作成

```bash
# 1. age鍵ペア生成（初回のみ）
age-keygen -o ~/.config/sops/age/keys.txt

# 2. 公開鍵を確認
cat ~/.config/sops/age/keys.txt | grep "public key:"
# 出力: age1abc...

# 3. .sops.yamlに公開鍵を設定
cat > .sops.yaml <<EOF
creation_rules:
  - path_regex: \.env\.dev(\.enc)?$
    age: age1abc...
EOF

# 4. 環境ファイル作成＆暗号化
cp .env.example .env.dev
nano .env.dev
sops -e .env.dev > .env.dev.enc

# 5. Gitにコミット
git add .env.dev.enc .sops.yaml
git commit -m "Add encrypted dev secrets"
git push

# 6. 平文の.env.devは削除
rm .env.dev
```

### 開発者Bがシークレットを使用

```bash
# 1. リポジトリクローン
git clone https://github.com/owner/repo.git
cd repo

# 2. age秘密鍵を受け取る
# 開発者Aから安全な方法で秘密鍵を受け取る
# （Slack DM、1Password、etc.）

# 3. 秘密鍵を配置
mkdir -p ~/.config/sops/age
nano ~/.config/sops/age/keys.txt  # 秘密鍵を貼り付け
chmod 600 ~/.config/sops/age/keys.txt

# 4. 復号化してデプロイ
sops -d .env.dev.enc > .env
./scripts/deploy-dev.sh
```

### シークレット更新

```bash
# 1. 暗号化ファイルを編集
sops .env.dev.enc

# 2. 変更を保存（自動的に再暗号化）

# 3. Gitにコミット
git add .env.dev.enc
git commit -m "Update API key"
git push
```

### チームメンバー追加

```bash
# 1. 新メンバーの公開鍵を取得
# 新メンバー: age-keygen -o ~/.config/sops/age/keys.txt
# 新メンバー: cat ~/.config/sops/age/keys.txt | grep "public key:"
# 出力: age1newmember...

# 2. .sops.yamlに公開鍵を追加
nano .sops.yaml
# age: >-
#   age1abc...,
#   age1newmember...

# 3. 既存の暗号化ファイルを再暗号化
sops updatekeys .env.dev.enc

# 4. コミット
git add .sops.yaml .env.dev.enc
git commit -m "Add new team member to secrets"
git push
```

## ベストプラクティス

### セキュリティ

1. **秘密鍵を安全に保管**
   ```bash
   # パーミッション設定
   chmod 600 ~/.config/sops/age/keys.txt

   # バックアップ（暗号化して保存）
   cp ~/.config/sops/age/keys.txt ~/backup/age-keys-$(date +%Y%m%d).txt
   ```

2. **平文ファイルを絶対にコミットしない**
   ```bash
   # .gitignoreに追加（必須）
   .env
   .env.local
   .env.dev
   .env.prod
   secrets/
   ```

3. **環境ごとに異なる鍵を使用**
   ```yaml
   # Dev鍵とProd鍵を分離
   - path_regex: \.env\.dev(\.enc)?$
     age: age1dev...
   - path_regex: \.env\.prod(\.enc)?$
     age: age1prod...
   ```

4. **定期的な鍵ローテーション**
   ```bash
   # 新しい鍵ペア生成
   age-keygen -o ~/.config/sops/age/keys-new.txt

   # .sops.yamlを更新
   # 暗号化ファイルを再暗号化
   sops updatekeys .env.dev.enc

   # 古い鍵を削除
   ```

### 運用

1. **シークレット変更履歴の記録**
   ```bash
   # 変更内容を詳細にコミットメッセージに記載
   git commit -m "Update database password

   - Reason: Scheduled rotation
   - Changed by: @username
   - Date: 2025-10-25"
   ```

2. **復号化後は即削除**
   ```bash
   # デプロイスクリプトで自動削除
   sops -d .env.dev.enc > .env
   ./deploy.sh
   rm .env  # 必ず削除
   ```

3. **CI/CD環境での使用**
   ```bash
   # GitHub Secretsに秘密鍵を保存
   # Workflow:
   - name: Decrypt secrets
     run: |
       echo "${{ secrets.AGE_SECRET_KEY }}" > /tmp/age-key.txt
       export SOPS_AGE_KEY_FILE=/tmp/age-key.txt
       sops -d .env.prod.enc > .env

   - name: Deploy
     run: ./deploy.sh

   - name: Cleanup
     if: always()
     run: rm -f .env /tmp/age-key.txt
   ```

4. **シークレットの監査**
   ```bash
   # 誰がいつ変更したか確認
   git log --oneline .env.dev.enc

   # 差分確認（メタデータのみ）
   git diff HEAD~1 .env.dev.enc
   ```

### ファイル構成

```
project/
├── .sops.yaml              # SOPS設定（コミット✅）
├── .env.example            # テンプレート（コミット✅）
├── .env.dev.enc           # 暗号化Dev環境変数（コミット✅）
├── .env.prod.enc          # 暗号化Prod環境変数（コミット✅）
├── .env                   # 復号化後（gitignore❌）
├── .env.dev               # 作業用（gitignore❌）
└── .env.prod              # 作業用（gitignore❌）
```

## トラブルシューティング

### エラー: `Failed to get the data key`

**原因**: 秘密鍵が見つからない、または不正

**解決方法**:
```bash
# 1. 秘密鍵の存在確認
ls -la ~/.config/sops/age/keys.txt

# 2. パーミッション確認
chmod 600 ~/.config/sops/age/keys.txt

# 3. 環境変数確認
echo $SOPS_AGE_KEY_FILE

# 4. 秘密鍵の内容確認（最初の行）
head -1 ~/.config/sops/age/keys.txt
# 出力: # created: 2025-10-25T...
head -2 ~/.config/sops/age/keys.txt | tail -1
# 出力: # public key: age1xxx...
```

### エラー: `no matching creation rules`

**原因**: `.sops.yaml`の`path_regex`がファイル名にマッチしない

**解決方法**:
```bash
# 1. ファイル名確認
ls -la .env*

# 2. .sops.yamlのパス確認
cat .sops.yaml

# 3. 正規表現テスト
# ファイル: .env.dev.enc
# パターン: \.env\.dev(\.enc)?$
# マッチ: ✅

# 4. 明示的に鍵を指定
sops --age age1xxx... -e .env.dev > .env.dev.enc
```

### エラー: `MAC mismatch`

**原因**: ファイルが破損、または不正な秘密鍵

**解決方法**:
```bash
# 1. Git履歴から復元
git checkout HEAD -- .env.dev.enc

# 2. バックアップから復元
cp backup/.env.dev.enc .

# 3. 再作成
# 平文から再暗号化
```

### 復号化が遅い

**原因**: ファイルサイズが大きい

**解決方法**:
```bash
# シークレットのみ抽出
sops -d --extract '["DATABASE_URL"]' .env.dev.enc

# または特定のキーだけ復号化
sops -d .env.dev.enc | grep DATABASE_URL
```

### チームメンバーが復号化できない

**原因**: 公開鍵が`.sops.yaml`に追加されていない

**解決方法**:
```bash
# 1. メンバーの公開鍵を確認
# メンバー側: age-keygen -y ~/.config/sops/age/keys.txt

# 2. .sops.yamlに追加
nano .sops.yaml

# 3. 既存ファイルを再暗号化
sops updatekeys .env.dev.enc

# 4. コミット＆プッシュ
git add .sops.yaml .env.dev.enc
git commit -m "Add team member to secrets"
git push
```

## 参考資料

### 公式ドキュメント

- [SOPS GitHub](https://github.com/getsops/sops)
- [age GitHub](https://github.com/FiloSottile/age)
- [age Specification](https://age-encryption.org/)

### チュートリアル

- [A Comprehensive Guide to SOPS](https://blog.gitguardian.com/a-comprehensive-guide-to-sops/)
- [Using SOPS with age](https://github.com/getsops/sops#encrypting-using-age)

### セキュリティベストプラクティス

- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### 関連ドキュメント

- [デプロイメントガイド](./deployment.md)
