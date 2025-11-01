"""SPA対応の静的ファイルサーバー"""

from typing import Any, MutableMapping

from fastapi import Response
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """
    SPA対応の静的ファイルサーバー

    404エラーが発生した場合にindex.htmlを返すことで、
    React Routerのhistory modeをサポート
    """

    async def get_response(
        self, path: str, scope: MutableMapping[str, Any]
    ) -> Response:
        try:
            return await super().get_response(path, scope)
        except FastAPIHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise ex
