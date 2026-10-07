"""The API can start processes and a Claude run, so it must only answer this machine's own UI.

- Host must be 127.0.0.1/localhost (stops DNS-rebinding: a hostile page resolving its own name to 127.0.0.1).
- Every state-changing request must carry the X-Leads-UI header and, when the browser sends one, an Origin
  that is this app. A custom header cannot be sent cross-site without a CORS preflight, and no CORS is
  granted, so another tab cannot POST here (a plain form or multipart POST would otherwise get through).
"""
from leadgen import config
from starlette.responses import JSONResponse

HOSTS = ("127.0.0.1", "localhost")
ORIGINS = {f"http://{h}:{p}" for h in HOSTS for p in (config.UI_PORT, config.UI_DEV_PORT)}
SAFE = ("GET", "HEAD", "OPTIONS")


class Guard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope["headers"]}
        host = headers.get("host", "").rsplit(":", 1)[0] if not headers.get("host", "").startswith("[") else ""
        if host not in HOSTS:
            return await JSONResponse({"error": "This app only answers on 127.0.0.1."}, 400)(scope, receive, send)
        if scope["method"] not in SAFE:
            origin = headers.get("origin")
            if headers.get("x-leads-ui") != "1" or (origin is not None and origin not in ORIGINS):
                return await JSONResponse({"error": "Request not allowed from this origin."}, 403)(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"] += [(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer"),
                                       (b"cross-origin-resource-policy", b"same-origin")]
            await send(message)

        await self.app(scope, receive, send_with_headers)
