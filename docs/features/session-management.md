# Session Management

本テンプレートのセッション管理システム。RedisではなくRDB（PostgreSQL）を使用し、Fernet暗号化、CSRF保護、セッションフィンガープリント検証を実装。

## アーキテクチャ

### システム構成

```
┌────────────────────────────────────────────────────┐
│ Client (Browser)                                   │
│  - Cookie: session_id                              │
└────────────────┬───────────────────────────────────┘
                 │ HTTP Request (Cookie + User-Agent + IP)
                 ↓
┌────────────────────────────────────────────────────┐
│ session_middleware (app/main.py)                   │
│  - Cookieからsession_id取得                        │
│  - クライアントIP取得                              │
│  - SessionServiceでセッション取得                  │
│  - request.state.sessionに設定                     │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ SessionService                                     │
│  (app/infrastructure/repositories/               │
│   session_repository.py)                           │
│  - セッション作成・取得・更新・削除                │
│  - フィンガープリント検証                          │
│  - CSRF検証                                        │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ SessionEncryption                                  │
│  (app/infrastructure/security/encryption.py)      │
│  - Fernet対称暗号化                                │
│  - encrypt() / decrypt()                           │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ PostgreSQL (sessions table)                        │
│  - session_id (PK, index)                          │
│  - data (Text, 暗号化されたJSON)                   │
│  - expires_at (DateTime, index)                    │
│  - fingerprint (String, SHA256)                    │
│  - csrf_token (String)                             │
│  - created_at, updated_at (TimeStampMixin)         │
└────────────────────────────────────────────────────┘
```

## セッションモデル

### データベーススキーマ

**場所**: `app/infrastructure/database/models/session.py`

```python
class Session(Base, TimeStampMixin):
    """
    セッションモデル

    Attributes:
        session_id: セッションID（主キー、64文字HEX）
        data: 暗号化されたセッションデータ（JSON）
        expires_at: セッション有効期限
        fingerprint: セッションフィンガープリント（User-Agent + IPのSHA256ハッシュ）
        csrf_token: CSRFトークン（64文字HEX）
    """
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # 暗号化されたJSON
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256ハッシュ
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
```

**インデックス**:
- `session_id`: プライマリーキー、高速検索
- `expires_at`: 期限切れセッションの効率的な削除

## セキュリティ機構

### 1. Fernet暗号化

**場所**: `app/infrastructure/security/encryption.py`

**クラス**: `SessionEncryption`

```python
class SessionEncryption:
    """
    セッションデータの暗号化/復号化

    Fernet (対称暗号化) を使用してセッションデータを安全に保存
    """
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key is None:
            settings = get_settings()
            encryption_key = settings.SESSION_ENCRYPTION_KEY

        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
            self.enabled = True
        else:
            self.cipher = None
            self.enabled = False
            logger.warning("Session encryption disabled")

    def encrypt(self, data: dict[str, Any]) -> str:
        """セッションデータを暗号化"""
        if not self.enabled or not self.cipher:
            logger.warning("Storing session data without encryption")
            return json.dumps(data, ensure_ascii=False)

        json_str = json.dumps(data, ensure_ascii=False)
        encrypted = self.cipher.encrypt(json_str.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_data: str) -> dict[str, Any]:
        """暗号化されたセッションデータを復号化"""
        if not self.enabled or not self.cipher:
            return json.loads(encrypted_data)

        decrypted = self.cipher.decrypt(encrypted_data.encode("utf-8"))
        json_str = decrypted.decode("utf-8")
        return json.loads(json_str)
```

**暗号化キーの生成**:
```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(key.decode())  # .envのSESSION_ENCRYPTION_KEYに設定
```

**特徴**:
- 対称鍵暗号（Fernet）
- Base64エンコード
- 暗号化無効時は警告ログ出力（非推奨）

### 2. CSRFトークン保護

**トークン生成**:
```python
def generate_csrf_token() -> str:
    """CSRFトークンを生成（64文字HEX）"""
    return secrets.token_hex(32)
```

**検証フロー**:
```python
session_data = service.get_session(
    session_id,
    user_agent,
    client_ip,
    verify_csrf=True,           # CSRF検証を有効化
    csrf_token=request_csrf_token  # リクエストから取得したトークン
)
```

**使用例**（POSTリクエスト）:
```python
@router.post("/update-profile")
async def update_profile(
    csrf_token: str = Header(..., alias="X-CSRF-Token"),
    deps: DBWithSession = Depends(get_db_with_session)
):
    service = SessionService(deps.db)
    session_data = service.get_session(
        deps.session_id,
        deps.user_agent,
        deps.client_ip,
        verify_csrf=True,
        csrf_token=csrf_token
    )
    if not session_data:
        raise UnauthorizedError("Invalid CSRF token")
    # ...
```

### 3. セッションフィンガープリント検証

**フィンガープリント生成**:
```python
def generate_fingerprint(user_agent: Optional[str], client_ip: Optional[str]) -> str:
    """
    セッションフィンガープリントを生成

    User-AgentとクライアントIPのSHA256ハッシュを生成
    セッション固定攻撃への対策として使用

    Returns:
        SHA256ハッシュ（64文字のHEX文字列）
    """
    ua = user_agent or "unknown"
    ip = client_ip or "unknown"
    fingerprint_str = f"{ua}|{ip}"
    return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()
```

**検証**:
```python
def verify_fingerprint(
    stored_fingerprint: str,
    user_agent: Optional[str],
    client_ip: Optional[str]
) -> bool:
    """フィンガープリントを検証（定数時間比較）"""
    current_fingerprint = generate_fingerprint(user_agent, client_ip)
    return secrets.compare_digest(stored_fingerprint, current_fingerprint)
```

**セキュリティ効果**:
- セッション固定攻撃の防止
- セッションハイジャック検知
- 定数時間比較（secrets.compare_digest）でタイミング攻撃を防止

### 4. セッションID再生成

**ログイン成功時の推奨処理**:
```python
def regenerate_session_id(
    old_session_id: str,
    user_agent: Optional[str],
    client_ip: Optional[str]
) -> Optional[tuple[str, str]]:
    """
    セッションIDを再生成（セッション固定攻撃対策）

    Returns:
        (新しいsession_id, 新しいcsrf_token) のタプル
    """
    data = self.get_session(old_session_id, user_agent, client_ip)
    if data is None:
        return None

    self.delete_session(old_session_id)
    new_session_id, new_csrf_token = self.create_session(data, user_agent, client_ip)

    logger.info(f"Session ID regenerated: {old_session_id} -> {new_session_id}")
    return new_session_id, new_csrf_token
```

**使用例**:
```python
from app.utils.session_helper import regenerate_session_id

@router.post("/login")
async def login(
    credentials: LoginCredentials,
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    # 認証処理
    user = authenticate(credentials)

    # セッションID再生成（セッション固定攻撃対策）
    result = regenerate_session_id(db, request, response)
    if result:
        new_session_id, new_csrf_token = result
    else:
        # 既存セッションがない場合は新規作成
        from app.utils.session_helper import create_session
        new_session_id, new_csrf_token = create_session(
            db, response, request,
            data={"user_id": user.id}
        )

    return {"csrf_token": new_csrf_token}
```

## SessionService

**場所**: `app/infrastructure/repositories/session_repository.py`

### メソッド一覧

#### create_session

```python
def create_session(
    self,
    data: dict[str, Any],
    user_agent: Optional[str] = None,
    client_ip: Optional[str] = None,
    expire_seconds: Optional[int] = None,
) -> tuple[str, str]:
    """
    新しいセッションを作成

    Returns:
        (session_id, csrf_token) のタプル
    """
```

**使用例**:
```python
service = SessionService(db)
session_id, csrf_token = service.create_session(
    data={"user_id": 123, "role": "admin"},
    user_agent=request.headers.get("User-Agent"),
    client_ip="192.168.1.1",
    expire_seconds=3600  # 1時間（オプション）
)
```

#### get_session

```python
def get_session(
    self,
    session_id: str,
    user_agent: Optional[str] = None,
    client_ip: Optional[str] = None,
    verify_csrf: bool = False,
    csrf_token: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    セッションを取得

    Returns:
        セッションデータ、存在しないまたは無効な場合はNone
    """
```

**検証内容**:
1. セッションの存在確認
2. 有効期限チェック（期限切れの場合は削除）
3. フィンガープリント検証（不一致の場合は削除）
4. CSRF検証（verify_csrf=Trueの場合）

**使用例**:
```python
session_data = service.get_session(
    session_id="abc123...",
    user_agent=request.headers.get("User-Agent"),
    client_ip="192.168.1.1",
    verify_csrf=True,
    csrf_token=request.headers.get("X-CSRF-Token")
)

if session_data:
    user_id = session_data.get("user_id")
```

#### update_session

```python
def update_session(
    self,
    session_id: str,
    data: dict[str, Any],
    user_agent: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> bool:
    """
    セッションデータを更新

    Returns:
        更新成功時True
    """
```

#### delete_session

```python
def delete_session(self, session_id: str) -> bool:
    """
    セッションを削除

    Returns:
        削除成功時True
    """
```

#### cleanup_expired_sessions

```python
def cleanup_expired_sessions(self) -> int:
    """
    期限切れセッションをクリーンアップ

    Returns:
        削除されたセッション数
    """
```

**バッチ処理での使用**:
```python
# app/infrastructure/batch/tasks/cleanup_sessions.py
class CleanupSessionsTask(BaseTask):
    name = "cleanup_sessions"
    description = "期限切れセッションを削除"
    schedule = "0 * * * *"  # 毎時0分

    def run(self):
        db = next(get_db())
        try:
            service = SessionService(db)
            count = service.cleanup_expired_sessions()
            logger.info(f"Cleaned up {count} expired sessions")
        finally:
            db.close()
```

## セッションヘルパー

**場所**: `app/utils/session_helper.py`

FastAPIのRequest/Responseと統合するヘルパー関数群。

### create_session

```python
def create_session(
    db: DBSession,
    response: Response,
    request: Request,
    data: dict[str, Any],
) -> tuple[str, str]:
    """
    新しいセッションを作成してCookieに設定

    Returns:
        (session_id, csrf_token) のタプル
    """
```

**使用例**:
```python
from app.utils.session_helper import create_session

@router.post("/login")
async def login(
    credentials: LoginCredentials,
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    user = authenticate(credentials)

    session_id, csrf_token = create_session(
        db, response, request,
        data={"user_id": user.id, "role": user.role}
    )

    return {"csrf_token": csrf_token}
```

### get_session_data

```python
def get_session_data(
    db: DBSession,
    request: Request,
    verify_csrf: bool = False,
    csrf_token: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """セッションデータを取得"""
```

### update_session_data

```python
def update_session_data(
    db: DBSession,
    request: Request,
    data: dict[str, Any],
) -> bool:
    """セッションデータを更新"""
```

### delete_session

```python
def delete_session(
    db: DBSession,
    request: Request,
    response: Response,
) -> bool:
    """セッションを削除してCookieをクリア"""
```

**使用例（ログアウト）**:
```python
from app.utils.session_helper import delete_session

@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    delete_session(db, request, response)
    return {"message": "Logged out successfully"}
```

## セッションミドルウェア

**場所**: `app/main.py`

```python
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """
    セッション管理ミドルウェア

    DATABASE_URLが設定されている場合のみ、RDBベースのセッション管理を有効化
    """
    if settings.has_database:
        db = next(get_db())
        try:
            session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if session_id:
                service = SessionService(db)
                user_agent = request.headers.get("User-Agent")

                # クライアントIP取得（優先順位: CF-Connecting-IP > X-Forwarded-For > client.host）
                client_ip_headers = ["CF-Connecting-IP", "X-Forwarded-For"]
                client_ip = None
                for header in client_ip_headers:
                    client_ip = request.headers.get(header)
                    if client_ip:
                        break
                if not client_ip:
                    client_ip = request.client.host if request.client else None

                session_data = service.get_session(session_id, user_agent, client_ip)

                request.state.session = session_data or {}
                request.state.session_id = session_id
                request.state.client_ip = client_ip
                request.state.user_agent = user_agent
            else:
                request.state.session = {}

            response = await call_next(request)

            # セッションデータの永続化は各エンドポイントで明示的に実施
            # ミドルウェアでの自動保存は行わない（パフォーマンス対策）

            return response
        finally:
            db.close()
    else:
        request.state.session = None
        return await call_next(request)
```

**特徴**:
- 自動保存なし（パフォーマンス考慮）
- 各エンドポイントで明示的に保存
- request.stateにセッション情報を設定

## 依存性注入パターン

**場所**: `app/presentation/api/deps.py`

### get_session

```python
def get_session(request: Request) -> SessionSchema:
    """セッションデータを取得するdependency"""
    session = request.state.session
    if isinstance(session, SessionSchema):
        return session
    session_data: dict[str, Any] = session if session is not None else {}
    return SessionSchema(data=session_data)
```

### get_db_with_session

```python
@dataclass
class DBWithSession:
    db: Session
    session: SessionSchema

def get_db_with_session(
    db: Session = Depends(get_db),
    session: SessionSchema = Depends(get_session),
) -> Generator[DBWithSession, None, None]:
    """DBとセッションの両方を取得するdependency"""
    yield DBWithSession(db=db, session=session)
```

**使用例**:
```python
@router.get("/profile")
async def get_profile(deps: DBWithSession = Depends(get_db_with_session)):
    user_id = deps.session.data.get("user_id")
    if not user_id:
        raise UnauthorizedError("Not logged in")

    user = deps.db.query(User).filter_by(id=user_id).first()
    return user
```

## 実装例

### ログイン実装

```python
from app.utils.session_helper import create_session
from app.domain.exceptions.base import UnauthorizedError

@router.post("/login")
async def login(
    credentials: LoginCredentials,
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    # 認証処理
    user = db.query(User).filter_by(email=credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    # セッション作成
    session_id, csrf_token = create_session(
        db, response, request,
        data={"user_id": user.id, "role": user.role, "email": user.email}
    )

    return {
        "message": "Login successful",
        "csrf_token": csrf_token,
        "user": {"id": user.id, "email": user.email}
    }
```

### ログアウト実装

```python
from app.utils.session_helper import delete_session

@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    request: Request,
    response: Response
):
    delete_session(db, request, response)
    return {"message": "Logged out successfully"}
```

### 認証が必要なエンドポイント

```python
from app.domain.exceptions.base import UnauthorizedError

@router.get("/protected")
async def protected_endpoint(deps: DBWithSession = Depends(get_db_with_session)):
    user_id = deps.session.data.get("user_id")
    if not user_id:
        raise UnauthorizedError("Authentication required")

    # ビジネスロジック
    return {"message": "Authenticated", "user_id": user_id}
```

### セッションデータの更新

```python
from app.utils.session_helper import update_session_data

@router.post("/update-preferences")
async def update_preferences(
    preferences: UserPreferences,
    db: Session = Depends(get_db),
    request: Request
):
    # 既存セッションデータを取得
    from app.utils.session_helper import get_session_data
    session_data = get_session_data(db, request)
    if not session_data:
        raise UnauthorizedError("Not logged in")

    # セッションデータを更新
    session_data["preferences"] = preferences.dict()
    update_session_data(db, request, session_data)

    return {"message": "Preferences updated"}
```

## 設定

### 環境変数

```bash
# .env
SESSION_ENCRYPTION_KEY=your-fernet-key-here  # Fernet.generate_key()で生成
SESSION_COOKIE_NAME=session_id               # Cookie名（デフォルト）
SESSION_EXPIRE=86400                         # 有効期限（秒、デフォルト24時間）
```

### Fernet暗号化キーの生成

```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(f"SESSION_ENCRYPTION_KEY={key.decode()}")
```

## ベストプラクティス

### 1. ログイン時はセッションIDを再生成

```python
# ✅ GOOD: セッション固定攻撃対策
from app.utils.session_helper import regenerate_session_id

@router.post("/login")
async def login(...):
    # 認証処理
    regenerate_session_id(db, request, response)
```

### 2. 機密情報はセッションに保存しない

```python
# ❌ BAD: パスワードを保存
session_data = {"password": user.password}

# ✅ GOOD: 最小限の識別情報のみ
session_data = {"user_id": user.id, "role": user.role}
```

### 3. CSRF保護を有効化（POST/PUT/DELETE）

```python
# ✅ GOOD: 状態変更操作ではCSRF検証
@router.post("/delete-account")
async def delete_account(
    csrf_token: str = Header(..., alias="X-CSRF-Token"),
    deps: DBWithSession = Depends(get_db_with_session)
):
    service = SessionService(deps.db)
    session_data = service.get_session(
        deps.session_id, deps.user_agent, deps.client_ip,
        verify_csrf=True, csrf_token=csrf_token
    )
    if not session_data:
        raise UnauthorizedError("Invalid CSRF token")
```

### 4. 定期的に期限切れセッションをクリーンアップ

バッチタスクで自動削除（既に実装済み）。

## 参考資料

- [Architecture](../architecture.md) - Clean Architecture実装詳細
- [API Reference](../api-reference.md) - SessionSchema、ヘルパー関数
- [Batch System](batch-system.md) - 期限切れセッション自動削除
