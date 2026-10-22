from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.setting.service import NodeServiceSetting


def _load_node_setting(args: argparse.Namespace) -> tuple[NodeServiceSetting, Path]:
    # Imported here so `--help` does not load the resource layer
    from app.resource._global.setting import GlobalSetting

    GlobalSetting.load(args.setting_path)
    _node_setting = GlobalSetting.get_services().node
    _setting_path = GlobalSetting.get_setting_path()
    return _node_setting, _setting_path


# --------------------------------------------------
# fortress auth
# --------------------------------------------------


def _auth_init(args: argparse.Namespace) -> int:
    from app.service.node.service.auth import NodeAuth

    _setting, _base_dir = _load_node_setting(args)
    _created = NodeAuth.generate_master_file(_setting.auth, _base_dir)
    if _created is None:
        print("masterfile already exists, not overwritten", file=sys.stderr)
        return 1
    else:
        print(f"created {_created}")
        return 0


def _auth_list(args: argparse.Namespace) -> int:
    from app.service.node.service.auth import NodeAuth

    _setting, _base_dir = _load_node_setting(args)
    _auth = NodeAuth(_setting.auth, base_dir=_base_dir)
    for _t in _setting.auth.tokens:
        print(f"Token '{_t.name}'")
        print(f" - state: {_auth.state(_t.name)}")
        print(f" - expires: {_t.expires or '-'}")
        print(f" - description: {_t.description}")
    return 0


def _auth_show(args: argparse.Namespace) -> int:
    from app.service.node.service.auth import NodeAuth

    _setting, _base_dir = _load_node_setting(args)
    _auth = NodeAuth(_setting.auth, base_dir=_base_dir)
    try:
        print(_auth.token(args.name))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------
# fortress node
# --------------------------------------------------


def _node_start(args: argparse.Namespace) -> int:
    # Imported here so `fortress auth` works without the node extra (uvicorn, duckdb)
    from app.service.node.service.auth import NodeAuth
    from app.service.node.service.http import serve
    from app.service.node.service.service import NodeService

    _setting, _base_dir = _load_node_setting(args)
    _auth = NodeAuth(_setting.auth, base_dir=_base_dir)
    serve(
        service=NodeService(_setting),
        auth=_auth,
        host=args.host,
        port=args.port,
    )
    return 0


# --------------------------------------------------
# Parser
# --------------------------------------------------


def _build() -> argparse.ArgumentParser:
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
    _auth = _groups.add_parser(
        "auth",
        help="manage the tokens of the node",
    )
    _auth_cmds = _auth.add_subparsers(
        dest="command",
        required=True,
    )
    _init = _auth_cmds.add_parser(
        "init",
        parents=[_common],
        help="create the master key file",
    )
    _init.set_defaults(handler=_auth_init)
    _list = _auth_cmds.add_parser(
        "list",
        parents=[_common],
        help="list the tokens and their state",
    )
    _list.set_defaults(handler=_auth_list)
    _show = _auth_cmds.add_parser(
        "show",
        parents=[_common],
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

    return _parser


def main(argv: list[str] | None = None) -> int:
    _args = _build().parse_args(argv)
    return _args.handler(_args)


if __name__ == "__main__":
    raise SystemExit(main())
