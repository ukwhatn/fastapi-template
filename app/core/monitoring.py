"""監視ツール（Sentry, New Relic）の初期化"""

import os

import newrelic.agent
import sentry_sdk

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_monitoring() -> None:
    """
    Sentry/New Relicの初期化

    本番環境でのみ有効化され、環境変数が設定されていない場合はスキップされる
    """
    settings = get_settings()

    # New Relic
    if settings.is_production and settings.NEW_RELIC_LICENSE_KEY:
        os.environ["NEW_RELIC_LICENSE_KEY"] = settings.NEW_RELIC_LICENSE_KEY
        os.environ["NEW_RELIC_APP_NAME"] = settings.NEW_RELIC_APP_NAME

        newrelic_config = newrelic.agent.global_settings()
        newrelic_config.high_security = settings.NEW_RELIC_HIGH_SECURITY
        newrelic_config.monitor_mode = settings.NEW_RELIC_MONITOR_MODE
        newrelic_config.app_name = (
            f"{settings.NEW_RELIC_APP_NAME}[{settings.normalized_env_mode}]"
        )

        newrelic.agent.initialize(
            config_file="/etc/newrelic.ini", environment=settings.ENV_MODE
        )
        logger.info(f"New Relic is enabled (name: {newrelic_config.app_name})")
    else:
        logger.info(
            f"New Relic is disabled on {settings.ENV_MODE} mode"
            if not settings.is_production
            else "New Relic license key is not set"
        )

    # Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.normalized_env_mode,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            _experiments={
                "continuous_profiling_auto_start": True,
            },
        )
        logger.info(f"Sentry is enabled on {settings.normalized_env_mode} mode")
    else:
        logger.info(
            f"Sentry is disabled on {settings.normalized_env_mode} mode"
            if not settings.is_production
            else "Sentry DSN is not set"
        )
