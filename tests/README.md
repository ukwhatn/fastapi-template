# テストディレクトリ構造

このディレクトリには、プロジェクトの全テストが含まれています。

## ディレクトリ構造

```
tests/
├── conftest.py              # 全テスト共通のフィクスチャ（client, db_session等）
├── integration/             # 統合テスト
│   ├── conftest.py          # 統合テスト固有のフィクスチャ
│   └── api/                 # APIエンドポイントテスト
│       ├── v1/              # v1 APIテスト
│       │   └── test_root.py
│       ├── system/          # システムAPIテスト
│       │   ├── test_healthcheck.py
│       │   └── test_views.py
│       └── test_errors.py   # 共通エラーハンドリングテスト
└── unit/                    # 単体テスト
    ├── domain/              # Domain層のテスト（将来追加予定）
    ├── application/         # Application層のテスト（将来追加予定）
    ├── infrastructure/      # Infrastructure層のテスト
    │   ├── test_security.py
    │   └── test_session_repository.py
    └── presentation/        # Presentation層のテスト（将来追加予定）
```

## テストの種類

### 統合テスト (`integration/`)

APIエンドポイント全体の動作を検証するテストです。

- **配置ルール**: `tests/integration/api/`配下にAPIルーター構造をミラーリング
- **命名規則**: `test_*.py`
- **フィクスチャ**: `client`（TestClient）、`db_session`（テストDB）

**例**:
- `/v1/` エンドポイント → `tests/integration/api/v1/test_root.py`
- `/system/healthcheck/` → `tests/integration/api/system/test_healthcheck.py`

### 単体テスト (`unit/`)

個別のクラス・関数の動作を検証するテストです。

- **配置ルール**: `tests/unit/`配下にClean Architecture層構造をミラーリング
- **命名規則**: `test_*.py`
- **フィクスチャ**: 必要に応じて個別定義

**例**:
- `app/infrastructure/security/encryption.py` → `tests/unit/infrastructure/test_security.py`
- `app/infrastructure/repositories/session_repository.py` → `tests/unit/infrastructure/test_session_repository.py`

## テスト実行

```bash
# 全テスト実行
make test

# カバレッジレポート付き実行
make test:cov

# 特定のテストファイルのみ実行
uv run pytest tests/integration/api/v1/test_root.py -v

# 特定のテストクラスのみ実行
uv run pytest tests/integration/api/system/test_healthcheck.py::TestHealthCheck -v

# 特定のテストメソッドのみ実行
uv run pytest tests/integration/api/system/test_healthcheck.py::TestHealthCheck::test_healthcheck -v
```

## 新しいテストの追加

### 統合テストを追加する場合

1. 対応するAPIルーターに合わせてディレクトリを選択
2. `test_*.py`ファイルを作成
3. `client`フィクスチャを使用してHTTPリクエストをテスト

```python
from fastapi.testclient import TestClient

class TestYourEndpoint:
    def test_your_case(self, client: TestClient):
        response = client.get("/your/endpoint")
        assert response.status_code == 200
```

### 単体テストを追加する場合

1. テスト対象のコードが属するClean Architecture層に合わせてディレクトリを選択
2. `test_*.py`ファイルを作成
3. 必要に応じて`db_session`フィクスチャや独自フィクスチャを使用

```python
from app.infrastructure.security.encryption import generate_session_id

class TestYourFunction:
    def test_your_case(self):
        result = generate_session_id()
        assert len(result) == 128
```

## ベストプラクティス

1. **テストは独立させる**: 各テストは他のテストに依存せず、単独で実行できるようにする
2. **フィクスチャを活用**: 共通のセットアップ処理は`conftest.py`にフィクスチャとして定義
3. **テストDBを使用**: テストは専用PostgreSQLデータベース（pytest-{random}）を使用し、トランザクションベースで分離
4. **AAA パターン**: Arrange（準備）→ Act（実行）→ Assert（検証）の順で記述
5. **わかりやすい命名**: テストメソッド名は`test_`で始め、何をテストするか明確にする
6. **docstringを書く**: 各テストメソッドに日本語でテスト内容を記述

## 参考リンク

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest ベストプラクティス](https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/)
