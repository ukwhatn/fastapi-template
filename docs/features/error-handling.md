# Error Handling

本テンプレートのエラーハンドリング機構。Domain層の例外をHTTPレスポンスに自動変換し、統一されたエラーレスポンス形式を提供。

## アーキテクチャ

### レイヤーごとの役割

```
┌──────────────────────────────────────────────┐
│ Domain Layer (app/domain/exceptions/base.py) │
│  - DomainError (基底クラス)                  │
│  - NotFoundError, BadRequestError等          │
│  - フレームワーク非依存                      │
└──────────────────┬───────────────────────────┘
                   │ raise
                   ↓
┌──────────────────────────────────────────────┐
│ main.py (exception handlers)                 │
│  - DomainErrorをキャッチ                     │
│  - domain_error_to_api_error()で変換         │
└──────────────────┬───────────────────────────┘
                   │ convert
                   ↓
┌──────────────────────────────────────────────┐
│ Presentation Layer                           │
│  (app/presentation/exceptions/api_errors.py) │
│  - APIError (HTTPException継承)              │
│  - ErrorResponse (標準レスポンス形式)        │
└──────────────────────────────────────────────┘
```

## Domain層の例外

### DomainError（基底クラス）

**場所**: `app/domain/exceptions/base.py`

**定義**:
```python
class DomainError(Exception):
    """
    ドメイン層のベース例外

    Attributes:
        message: エラーメッセージ
        code: エラーコード（識別子）
        details: エラーの詳細情報（オプション）
    """
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)
```

**特徴**:
- 純粋なPython例外（フレームワーク非依存）
- 構造化されたエラー情報（message, code, details）
- detailsは辞書またはリストで複数エラーを保持可能

### 定義済み例外クラス

#### NotFoundError

```python
class NotFoundError(DomainError):
    """リソースが見つからない場合のエラー"""
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message=message, code="not_found", details=details)
```

**HTTPステータス**: 404

**使用例**:
```python
user = db.query(User).filter_by(id=user_id).first()
if not user:
    raise NotFoundError(f"User {user_id} not found", details={"user_id": user_id})
```

#### BadRequestError

```python
class BadRequestError(DomainError):
    """不正なリクエストエラー"""
    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message=message, code="bad_request", details=details)
```

**HTTPステータス**: 400

**使用例**:
```python
if quantity <= 0:
    raise BadRequestError("Quantity must be positive", details={"quantity": quantity})
```

#### UnauthorizedError

```python
class UnauthorizedError(DomainError):
    """認証エラー"""
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message=message, code="unauthorized", details=details)
```

**HTTPステータス**: 401

**使用例**:
```python
if not session.data.get("user_id"):
    raise UnauthorizedError("Please login to access this resource")
```

#### ForbiddenError

```python
class ForbiddenError(DomainError):
    """アクセス権限エラー"""
    def __init__(
        self,
        message: str = "Access forbidden",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message=message, code="forbidden", details=details)
```

**HTTPステータス**: 403

**使用例**:
```python
if user.role != "admin":
    raise ForbiddenError("Admin access required", details={"role": user.role})
```

#### ValidationError

```python
class ValidationError(BadRequestError):
    """バリデーションエラー"""
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.code = "validation_error"
```

**HTTPステータス**: 400

**使用例（複数エラー）**:
```python
errors = []
if len(password) < 8:
    errors.append({"field": "password", "error": "Too short"})
if "@" not in email:
    errors.append({"field": "email", "error": "Invalid format"})

if errors:
    raise ValidationError("Validation failed", details=errors)
```

## Presentation層のエラーハンドリング

### ErrorResponse

**場所**: `app/presentation/exceptions/api_errors.py`

**定義**:
```python
class ErrorResponse(BaseModel):
    """
    標準エラーレスポンス

    Attributes:
        status: ステータス（常に"error"）
        code: エラーコード
        message: エラーメッセージ
        details: エラーの詳細情報（オプション）
    """
    status: str = "error"
    code: str
    message: str
    details: Optional[list[dict[str, Any]] | dict[str, Any]] = None
```

**レスポンス例**:
```json
{
  "status": "error",
  "code": "not_found",
  "message": "User 123 not found",
  "details": {
    "user_id": 123
  }
}
```

### APIError

**定義**:
```python
class APIError(HTTPException):
    """
    API エラーの基底クラス

    Attributes:
        status_code: HTTPステータスコード
        error_code: エラーコード
        error_message: エラーメッセージ
        details: エラーの詳細情報
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_server_error"
    error_message: str = "Internal server error"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[list[dict[str, Any]] | dict[str, Any]] = None,
    ) -> None:
        self.error_message = message or self.error_message
        self.details = details
        super().__init__(status_code=self.status_code, detail=self.error_message)

    def to_response(self) -> ErrorResponse:
        """標準エラーレスポンス形式に変換"""
        return ErrorResponse(
            code=self.error_code,
            message=self.error_message,
            details=self.details
        )
```

### domain_error_to_api_error

**変換関数**:
```python
def domain_error_to_api_error(domain_error: DomainError) -> APIError:
    """
    ドメインエラーをAPIエラーに変換

    Args:
        domain_error: ドメイン層のエラー

    Returns:
        APIError: API層のエラー
    """
    # エラータイプに応じたHTTPステータスコードのマッピング
    status_map: dict[type, int] = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        BadRequestError: status.HTTP_400_BAD_REQUEST,
        UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
        ForbiddenError: status.HTTP_403_FORBIDDEN,
        ValidationError: status.HTTP_400_BAD_REQUEST,
    }

    # ステータスコードを決定
    status_code = status_map.get(
        type(domain_error), status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # APIErrorを生成
    api_error = APIError(
        message=domain_error.message,
        details=domain_error.details,
    )
    api_error.status_code = status_code
    api_error.error_code = domain_error.code
    api_error.error_message = domain_error.message

    return api_error
```

## main.pyの例外ハンドラー

### DomainError例外ハンドラー

```python
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> Response:
    """DomainError例外ハンドラ"""
    api_error = domain_error_to_api_error(exc)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )
```

### APIError例外ハンドラー（後方互換性）

```python
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> Response:
    """APIError例外ハンドラ（後方互換性のため保持）"""
    return Response(
        content=json.dumps(jsonable_encoder(exc.to_response())),
        status_code=exc.status_code,
        media_type="application/json",
    )
```

### HTTPException例外ハンドラー

```python
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    """HTTPException例外ハンドラ"""
    error = ErrorResponse(
        code="http_error",
        message=str(exc.detail),
    )
    return Response(
        content=json.dumps(jsonable_encoder(error)),
        status_code=exc.status_code,
        media_type="application/json",
    )
```

### Pydanticバリデーションエラーハンドラー

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    """バリデーションエラーハンドラ（Pydantic）"""
    error = ValidationError(
        message="Invalid request body",
        details=[
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ],
    )
    api_error = domain_error_to_api_error(error)
    return Response(
        content=json.dumps(jsonable_encoder(api_error.to_response())),
        status_code=api_error.status_code,
        media_type="application/json",
    )
```

**レスポンス例**:
```json
{
  "status": "error",
  "code": "validation_error",
  "message": "Invalid request body",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 未処理例外ハンドラー

```python
@app.middleware("http")
async def error_response(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Unhandled exception: {str(e)}", exc_info=e)

        error = ErrorResponse(
            code="internal_server_error",
            message="Internal server error occurred",
        )
        return Response(
            content=json.dumps(jsonable_encoder(error)),
            status_code=500,
            media_type="application/json",
        )
```

## 実装例

### 基本的な使用

```python
from app.domain.exceptions.base import NotFoundError, BadRequestError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise NotFoundError(f"User {user_id} not found", details={"user_id": user_id})

    return user

@router.post("/users")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=user_data.email).first():
        raise BadRequestError(
            "Email already exists",
            details={"email": user_data.email}
        )

    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    return user
```

### カスタム例外の作成

```python
# app/domain/exceptions/custom.py
from .base import DomainError

class ResourceConflictError(DomainError):
    """リソース競合エラー"""
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, code="resource_conflict", details=details)
```

**HTTPステータスコードのマッピング追加**:
```python
# app/presentation/exceptions/api_errors.py
def domain_error_to_api_error(domain_error: DomainError) -> APIError:
    status_map: dict[type, int] = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        BadRequestError: status.HTTP_400_BAD_REQUEST,
        UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
        ForbiddenError: status.HTTP_403_FORBIDDEN,
        ValidationError: status.HTTP_400_BAD_REQUEST,
        ResourceConflictError: status.HTTP_409_CONFLICT,  # 追加
    }
    # ...
```

**使用例**:
```python
from app.domain.exceptions.custom import ResourceConflictError

if db.query(User).filter_by(username=username).first():
    raise ResourceConflictError(
        f"Username '{username}' is already taken",
        details={"username": username}
    )
```

### 複数エラーの返却

```python
def validate_user_data(user_data: UserCreate) -> None:
    errors = []

    if len(user_data.password) < 8:
        errors.append({
            "field": "password",
            "error": "Password must be at least 8 characters"
        })

    if "@" not in user_data.email:
        errors.append({
            "field": "email",
            "error": "Invalid email format"
        })

    if user_data.age < 18:
        errors.append({
            "field": "age",
            "error": "Must be 18 or older"
        })

    if errors:
        raise ValidationError("Validation failed", details=errors)
```

**レスポンス**:
```json
{
  "status": "error",
  "code": "validation_error",
  "message": "Validation failed",
  "details": [
    {"field": "password", "error": "Password must be at least 8 characters"},
    {"field": "email", "error": "Invalid email format"},
    {"field": "age", "error": "Must be 18 or older"}
  ]
}
```

## ベストプラクティス

### 1. Domain例外を使用する

```python
# ❌ BAD: HTTPExceptionを直接raise
from fastapi import HTTPException

if not user:
    raise HTTPException(status_code=404, detail="User not found")

# ✅ GOOD: Domain例外を使用
from app.domain.exceptions.base import NotFoundError

if not user:
    raise NotFoundError("User not found")
```

### 2. 詳細情報を提供する

```python
# ❌ BAD: 最小限の情報のみ
raise NotFoundError("User not found")

# ✅ GOOD: 詳細情報を含める
raise NotFoundError(
    f"User {user_id} not found",
    details={"user_id": user_id, "requested_at": datetime.now().isoformat()}
)
```

### 3. 適切な例外クラスを選択する

```python
# ❌ BAD: 不適切な例外クラス
raise NotFoundError("Invalid email format")

# ✅ GOOD: ValidationErrorを使用
raise ValidationError("Invalid email format", details={"field": "email"})
```

### 4. セキュリティに配慮する

```python
# ❌ BAD: 内部実装の詳細を露出
raise BadRequestError(f"Database query failed: {str(e)}")

# ✅ GOOD: ユーザー向けメッセージ
logger.error(f"Database query failed: {str(e)}", exc_info=e)
raise BadRequestError("Invalid request parameters")
```

## 参考資料

- [Architecture](../architecture.md) - Clean Architecture実装詳細
- [API Reference](../api-reference.md) - 共通コンポーネント
