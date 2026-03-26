from fastapi import Request
from fastapi.templating import Jinja2Templates


def get_templates(request: Request) -> Jinja2Templates | None:
    """
    リクエストからJinja2Templatesインスタンスを取得

    Args:
        request: FastAPIのRequestオブジェクト

    Returns:
        Jinja2Templatesインスタンス、または無効な場合はNone
    """
    return getattr(request.app.state, "templates", None)
