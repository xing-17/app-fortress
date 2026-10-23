from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.service._common.auth import TokenAuth
    from app.setting.service import AuthSetting, McpHostServiceSetting, NodeServiceSetting


def _load_node_setting(args: argparse.Namespace) -> tuple[NodeServiceSetting, Path]:
    # Imported here so `--help` does not load the resource layer
    from app.resource._global.setting import GlobalSetting

    GlobalSetting.load(args.setting_path)
    _node_setting = GlobalSetting.get_services().node
    _setting_path = GlobalSetting.get_setting_path()
    return _node_setting, _setting_path


def _load_mcphost_setting(args: argparse.Namespace) -> McpHostServiceSetting:
    from app.resource._global.setting import GlobalSetting

    GlobalSetting.load(args.setting_path)
    _res: McpHostServiceSetting = GlobalSetting.get_services().mcphost
    return _res


def _load_auth_setting(args: argparse.Namespace) -> tuple[AuthSetting, Path]:
    from app.resource._global.setting import GlobalSetting

    GlobalSetting.load(args.setting_path)
    _services = GlobalSetting.get_services()
    _setting_path = GlobalSetting.get_setting_path()
    if args.service == "mcphost":
        return _services.mcphost.auth, _setting_path
    return _services.node.auth, _setting_path


# --------------------------------------------------
# fortress auth
# --------------------------------------------------


def _auth_init(args: argparse.Namespace) -> int:
    from app.service._common.auth import TokenAuth

    _auth_setting, _base_dir = _load_auth_setting(args)
    _created = TokenAuth.generate_master_file(_auth_setting, _base_dir)
    if _created is None:
        print("masterfile already exists, not overwritten", file=sys.stderr)
        return 1
    else:
        print(f"created {_created}")
        return 0


def _auth_list(args: argparse.Namespace) -> int:
    from app.service._common.auth import TokenAuth

    _auth_setting, _base_dir = _load_auth_setting(args)
    _auth = TokenAuth(_auth_setting, base_dir=_base_dir)
    for _t in _auth_setting.tokens:
        print(f"Token '{_t.name}'")
        print(f" - state: {_auth.state(_t.name)}")
        print(f" - expires: {_t.expires or '-'}")
        print(f" - description: {_t.description}")
    return 0


def _auth_show(args: argparse.Namespace) -> int:
    from app.service._common.auth import TokenAuth

    _auth_setting, _base_dir = _load_auth_setting(args)
    _auth = TokenAuth(_auth_setting, base_dir=_base_dir)
    try:
        print(_auth.token(args.name))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------
# fortress node
# --------------------------------------------------


def _build_auth(
    service: str,
    setting: AuthSetting,
    base_dir: Path,
) -> TokenAuth:
    # Only the auth part of services.yaml follows the file, the rest needs a restart
    from app.resource._global.setting import GlobalSetting
    from app.service._common.auth import TokenAuth
    from app.setting.service import ServicesSetting

    _file = GlobalSetting.services_setting_path
    if _file is None:
        return TokenAuth(setting, base_dir=base_dir)

    def _reload() -> AuthSetting:
        _services = ServicesSetting.from_yaml(path=_file)
        _res: AuthSetting = _services.mcphost.auth if service == "mcphost" else _services.node.auth
        return _res

    return TokenAuth(
        setting,
        base_dir=base_dir,
        reload=_reload,
        watch=[_file],
    )


def _node_start(args: argparse.Namespace) -> int:
    # Imported here so `fortress auth` works
    # without the node extra (uvicorn, duckdb)
    from app.resource._global.setting import GlobalSetting
    from app.service.machine.service.service import MachineService
    from app.service.node.service.http import serve
    from app.service.node.service.service import NodeService

    _setting, _base_dir = _load_node_setting(args)
    _auth = _build_auth("node", _setting.auth, _base_dir)
    _machine = MachineService(GlobalSetting.get_services().machine)
    serve(
        service=NodeService(_setting, machine=_machine),
        auth=_auth,
        host=args.host,
        port=args.port,
    )
    return 0


# --------------------------------------------------
# fortress mcphost
# --------------------------------------------------


def _mcphost_start(args: argparse.Namespace) -> int:
    # Imported here so the other commands work without the mcphost extra (mcp, httpx)
    from app.service.mcphost.service.http import serve
    from app.service.mcphost.service.service import McpHostService

    _setting = _load_mcphost_setting(args)
    try:
        _auth = _build_auth("mcphost", _setting.auth, _auth_base_dir())
        _service = McpHostService(_setting, node=args.node, auth=_auth)
        serve(
            service=_service,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
        )
    except (ValueError, OSError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


def _auth_base_dir() -> Path:
    from app.resource._global.setting import GlobalSetting

    return GlobalSetting.get_setting_path()


# --------------------------------------------------
# All service control
# --------------------------------------------------


def _up(args: argparse.Namespace) -> int:
    import signal
    import socket
    import subprocess
    import time

    _base = [sys.executable, "-m", "app.cline"]
    _common = ["--setting-path", args.setting_path] if args.setting_path else []
    _procs: list[subprocess.Popen] = []

    def _wait_port(host: str, port: int, timeout: float = 30.0) -> bool:
        _end = time.monotonic() + timeout
        while time.monotonic() < _end:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return True
            except OSError:
                time.sleep(0.3)
        return False

    def _stop(*_: object) -> None:
        for _p in _procs:
            if _p.poll() is None:
                _p.send_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    _node_setting, _ = _load_node_setting(args)
    _procs.append(subprocess.Popen([*_base, "node", "start", *_common]))
    if not _wait_port(_node_setting.host, _node_setting.port):
        _stop()
        print("node did not come up", file=sys.stderr)
        return 1
    _procs.append(subprocess.Popen([*_base, "mcphost", "start", *_common]))

    # 任何一个退出就带停另一个
    while all(_p.poll() is None for _p in _procs):
        time.sleep(0.5)
    _stop()
    return max((_p.wait() for _p in _procs), default=0)


# --------------------------------------------------
# Parser
# --------------------------------------------------


def _build_cline() -> argparse.ArgumentParser:
    _common = argparse.ArgumentParser(add_help=False)
    _common.add_argument(
        "--setting-path",
        default=None,
        help="settings directory, default as the node",
    )

    # Build the main parser for the fortress CLI
    _parser = argparse.ArgumentParser(
        prog="fortress",
        description="Fortress command line",
    )
    _groups = _parser.add_subparsers(
        dest="group",
        required=True,
    )

    # Auth group
    _service_arg = argparse.ArgumentParser(add_help=False)
    _service_arg.add_argument(
        "--service",
        choices=["node", "mcphost"],
        default="node",
        help="whose tokens, the node's (services) or the MCP host's (users), default node",
    )
    _auth = _groups.add_parser(
        "auth",
        help="manage the tokens of the node or the MCP host",
    )
    _auth_cmds = _auth.add_subparsers(
        dest="command",
        required=True,
    )
    _init = _auth_cmds.add_parser(
        "init",
        parents=[_common, _service_arg],
        help="create the master key file",
    )
    _init.set_defaults(handler=_auth_init)
    _list = _auth_cmds.add_parser(
        "list",
        parents=[_common, _service_arg],
        help="list the tokens and their state",
    )
    _list.set_defaults(handler=_auth_list)
    _show = _auth_cmds.add_parser(
        "show",
        parents=[_common, _service_arg],
        help="print the token of an entry",
    )
    _show.add_argument("name")
    _show.set_defaults(handler=_auth_show)

    # Node group
    _node = _groups.add_parser(
        "node",
        help="run the data node",
    )
    _node_cmds = _node.add_subparsers(
        dest="command",
        required=True,
    )
    _start = _node_cmds.add_parser(
        "start",
        parents=[_common],
        help="start the node until interrupted",
    )
    _start.add_argument(
        "--host",
        default=None,
        help="listen host, default from the setting",
    )
    _start.add_argument(
        "--port",
        type=int,
        default=None,
        help="listen port, default from the setting",
    )
    _start.set_defaults(handler=_node_start)

    # Mcphost group
    _mcphost = _groups.add_parser(
        "mcphost",
        help="run the MCP host in front of a node",
    )
    _mcphost_cmds = _mcphost.add_subparsers(
        dest="command",
        required=True,
    )
    _mcphost_run = _mcphost_cmds.add_parser(
        "start",
        parents=[_common],
        help="start the MCP host until interrupted",
    )
    _mcphost_run.add_argument(
        "--node",
        default=None,
        help="serve only this node of the setting, default all of them",
    )
    _mcphost_run.add_argument(
        "--host",
        default=None,
        help="listen host, default from the setting",
    )
    _mcphost_run.add_argument(
        "--port",
        type=int,
        default=None,
        help="listen port, default from the setting",
    )
    _mcphost_run.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug"],
        help="log level of the HTTP server",
    )
    _mcphost_run.set_defaults(handler=_mcphost_start)

    # Up command
    _up_cmd = _groups.add_parser(
        "up",
        parents=[_common],
        help="start all services together",
    )
    _up_cmd.set_defaults(handler=_up)

    return _parser


def main(argv: list[str] | None = None) -> int:
    _args = _build_cline().parse_args(argv)
    return _args.handler(_args)


if __name__ == "__main__":
    raise SystemExit(main())
