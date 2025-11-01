# CI/CD最適化ドキュメント

最終更新: 2025-11-01

## 概要

このドキュメントでは、GitHub Actionsワークフローのキャッシュ最適化について説明します。

## 実施した最適化

### P0: 最優先修正

#### 1. ci_docker-test.ymlのキャッシュ修正

**問題点**:
- `actions/cache@v4`を使用していたが機能していなかった
- `hashFiles('docker/**', ...)`が無効（dockerディレクトリが存在しない）
- 毎回5-10分のフルビルドが発生

**修正内容**:
- `docker/build-push-action@v6`でGHA cacheを使用
- `scope=docker-test`でキャッシュスコープを分離
- `make compose:build`を`make compose:up`に変更（ビルド済みイメージを使用）

**効果**: 5-10分 → 1-2分（80-90%短縮）

#### 2. cd_builder.ymlのキャッシュスコープ分離

**問題点**:
- キャッシュスコープが明示的に指定されていなかった
- 他のワークフローとキャッシュが混在する可能性

**修正内容**:
- `scope=cd-builder`を明示的に指定
- docker-testのキャッシュ（scope=docker-test）と分離

**効果**: キャッシュの予測可能性と効率が向上

### P1: 高優先度（品質向上）

#### 3. ci_frontend.ymlの追加

**背景**:
- バックエンドはlint、type-check、security、testが完備
- フロントエンドはビルドのみで品質チェックがなかった

**実装内容**:
- ESLintによるコード品質チェック
- TypeScriptによる型チェック
- pnpmキャッシュで高速化（`setup-node@v4`のcache機能）
- lintとtype-checkを並列実行

**効果**: フロントエンドの品質向上、早期エラー検出

#### 4. ci.ymlへのフロントエンドジョブ追加

**実装内容**:
- `frontend: uses: ./.github/workflows/ci_frontend.yml`を追加
- 既存のバックエンドジョブと並列実行

**効果**: PRごとにフロントエンドの品質チェックを自動実施

## キャッシュ戦略

### GitHub Actions Cache（GHA Cache）

**特徴**:
- GitHub Actionsのキャッシュストレージを使用
- リポジトリあたり10GBまで無料
- LRU方式で自動削除
- `mode=max`で全レイヤーをキャッシュ

### キャッシュスコープ設計

| ワークフロー | スコープ | 用途 |
|------------|---------|------|
| ci_docker-test | `docker-test` | Dockerインテグレーションテスト用イメージ |
| cd_builder | `cd-builder` | 本番デプロイ用イメージ |
| ci_frontend | Node.js cache（自動） | pnpm依存関係 |
| その他CI | uv cache（自動） | Python依存関係 |

**スコープ分離の利点**:
1. ワークフローごとに独立したキャッシュ
2. キャッシュの予測可能性向上
3. 不要なキャッシュ無効化を防止

### キャッシュキーの設計

#### ci_docker-test.yml

```yaml
cache-from: type=gha,scope=docker-test
cache-to: type=gha,mode=max,scope=docker-test
```

**キャッシュ無効化条件**:
- Dockerfileの変更
- uv.lockの変更
- frontend/pnpm-lock.yamlの変更

#### cd_builder.yml

```yaml
cache-from: type=gha,scope=cd-builder
cache-to: type=gha,mode=max,scope=cd-builder
```

**キャッシュ無効化条件**:
- Dockerfileの変更
- uv.lockの変更
- frontend/pnpm-lock.yamlの変更

#### ci_frontend.yml

```yaml
uses: actions/setup-node@v4
with:
  cache: 'pnpm'
  cache-dependency-path: frontend/pnpm-lock.yaml
```

**キャッシュ無効化条件**:
- frontend/pnpm-lock.yamlの変更

## メンテナンスガイド

### キャッシュの手動クリア

キャッシュ破損や大きな変更時にキャッシュを手動でクリアする方法：

1. **GitHub Web UIから**:
   - リポジトリの「Actions」タブ → 「Caches」
   - 該当するキャッシュを選択して削除

2. **GitHub CLIから**:
   ```bash
   # 全キャッシュをリスト
   gh cache list

   # 特定のキャッシュを削除
   gh cache delete <cache-id>

   # すべてのキャッシュを削除
   gh cache delete --all
   ```

3. **スコープ名を変更**:
   ```yaml
   # 例: docker-test → docker-test-v2
   cache-from: type=gha,scope=docker-test-v2
   cache-to: type=gha,mode=max,scope=docker-test-v2
   ```

### キャッシュ効果の確認

GitHub Actions Insightsでキャッシュヒット率を確認：

1. リポジトリの「Insights」タブ → 「Actions」
2. ワークフローを選択
3. 実行時間の推移を確認

**期待されるキャッシュヒット時の実行時間**:
- ci_docker-test: 1-2分
- cd_builder: 5-10分（multi-platform buildのため）
- ci_frontend: 30秒-1分

### トラブルシューティング

#### キャッシュがヒットしない

**原因1**: 依存関係ファイルが変更された
- 解決策: 意図的な変更なので、初回ビルド時間は長くなる

**原因2**: キャッシュが削除された（10GB制限、または7日間未使用）
- 解決策: 再度ビルドしてキャッシュを再作成

**原因3**: Dockerfileの変更
- 解決策: マルチステージビルドの各ステージが独立してキャッシュされるため、変更箇所以降のみ再ビルド

#### ビルドが遅い

**原因1**: multi-platform build（linux/amd64, linux/arm64）
- cd_builderは2つのアーキテクチャを並列ビルドするため、時間がかかる
- 解決策: 必要に応じてplatformsを削減

**原因2**: 依存関係のビルド（psycopg2-binary、rolldown-vite）
- 解決策: キャッシュが効けば改善される

**原因3**: GitHub Actions Runnerの負荷
- 解決策: 時間帯を変更するか、self-hosted runnerを検討

## 今後の最適化案

### 1. Dockerビルドの並列化（高難易度）

**概要**: フロントエンドとバックエンドのビルドを完全に分離

**メリット**:
- ビルド時間を30-40%短縮可能

**デメリット**:
- Dockerfile構造の大幅な変更が必要
- 複雑性の増加

**実装方針**:
1. フロントエンドビルドをGitHub Actions側で実行
2. ビルド成果物をartifactとして保存
3. Dockerfileではビルド済み成果物をコピーするだけ

### 2. キャッシュの高度な管理

**概要**: キャッシュの優先度付けと自動クリーンアップ

**実装方針**:
1. 重要なキャッシュに明示的なprefixを付与
2. 月次で古いキャッシュをクリーンアップするワークフロー

### 3. self-hosted runnerの導入

**概要**: 自社サーバーでGitHub Actions Runnerを実行

**メリット**:
- ビルド速度の向上
- キャッシュの永続化
- コスト削減（大規模プロジェクトの場合）

**デメリット**:
- 運用コストの増加
- セキュリティリスク

## 参考資料

- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [GitHub Actions Cache](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)
- [BuildKit Cache](https://docs.docker.com/build/cache/backends/gha/)
- [setup-uv](https://github.com/astral-sh/setup-uv)
- [pnpm action-setup](https://github.com/pnpm/action-setup)

## 変更履歴

| 日付 | 変更内容 | コミット |
|------|---------|---------|
| 2025-11-01 | 初版作成 | - |
| 2025-11-01 | ci_docker-testのキャッシュ修正 | 6020711 |
| 2025-11-01 | cd_builderのキャッシュスコープ分離 | c6ec2c7 |
| 2025-11-01 | ci_frontend.yml追加 | 00e404f |
| 2025-11-01 | ci.ymlにフロントエンドジョブ追加 | f27b49f |
