from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.database import get_db
from app.presentation.schemas.system import DatabaseStatus, HealthCheckResponse

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.get("/", response_model=HealthCheckResponse)
async def healthcheck(request: Request, response: Response) -> HealthCheckResponse:
    """
    ヘルスチェックエンドポイント

    - DB接続状況
    - アプリケーションuptime
    - 環境情報を返す

    DB接続に失敗した場合は503 Service Unavailableを返す
    """
    # uptime計算
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = 0.0
    if start_time:
        uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

    # DB接続チェック
    db_status = DatabaseStatus(status="healthy", connection=True, error=None)
    overall_status: str = "ok"

    if settings.has_database:
        try:
            db_gen = get_db()
            db: Session = next(db_gen)
            try:
                # 軽量なDB接続テスト
                db.execute(text("SELECT 1"))
                db_status.status = "healthy"
                db_status.connection = True
            except Exception as e:
                logger.error(f"Database health check failed: {e}", exc_info=True)
                db_status.status = "unhealthy"
                db_status.connection = False
                db_status.error = str(e)
                overall_status = "unhealthy"
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        except Exception as e:
            logger.error(f"Database connection failed: {e}", exc_info=True)
            db_status.status = "unhealthy"
            db_status.connection = False
            db_status.error = f"DB not configured: {str(e)}"
            overall_status = "unhealthy"
    else:
        db_status.status = "healthy"
        db_status.connection = False
        db_status.error = "Database disabled"

    # DB接続失敗時は503を返す
    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime_seconds,
        database=db_status,
        environment=settings.normalized_env_mode,
    )
