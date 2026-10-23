from __future__ import annotations

import uvicorn

from app.service.mcphost.service.service import McpHostService


def serve(
    service: McpHostService,
    host: str | None = None,
    port: int | None = None,
    log_level: str = "info",
) -> None:
    """
    Start the service, serve MCP over streamable HTTP until interrupted, stop the service

    Host and port default to the service setting.

    """
    _setting = service.setting
    _host: str = host or _setting.host
    service.start()
    try:
        uvicorn.run(
            service.asgi_app(_host),
            host=_host,
            port=port or _setting.port,
            log_level=log_level,
        )
    finally:
        service.stop()
