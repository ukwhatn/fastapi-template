"""FastAPIアプリケーションのエントリーポイント"""

from app.core.app_factory import create_app
from app.core.monitoring import init_monitoring

# 監視ツール初期化（アプリ生成前）
init_monitoring()

# アプリ生成
app = create_app()
