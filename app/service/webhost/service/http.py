from __future__ import annotations

import uvicorn

from app.service.webhost.service.service import WebHostService


def serve(
    service: WebHostService,
    host: str | None = None,
    port: int | None = None,
    log_level: str = "info",
) -> None:
    """
    Start the service, serve the web console until interrupted, stop the service

    Host and port default to the service setting.

    """
    _setting = service.setting
    service.start()
    try:
        uvicorn.run(
            service.asgi_app(),
            host=host or _setting.host,
            port=port or _setting.port,
            log_level=log_level,
        )
    finally:
        service.stop()
