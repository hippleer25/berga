"""
Starlette middleware that reads Accept-Language and stores the
resolved locale in a context variable via i18n.set_locale().
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from i18n import parse_accept_language, set_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("accept-language")
        locale = parse_accept_language(header)
        set_locale(locale)
        response: Response = await call_next(request)
        return response
