from __future__ import annotations

from namel3ss.cli.json_io import dumps_pretty
from namel3ss.traces.plain import format_plain
from namel3ss.version import get_version

def print_usage() -> None:
    usage = """Usage:
  n3 <command> [file.ai]
  python -m namel3ss <command> [file.ai]

namel3ss is an AI-native programming language. Every valid .ai file is an application. Studio is optional (inspector only; browser renders the app).

Start
  n3 new <template> <name>        # scaffold a project
  n3 kb                           # knowledge template
  n3 ops                          # operations template
  n3 aid                          # support template
  n3 list                         # list templates
  n3 run [file.ai]                # run app in browser (default: ./app.ai)
  n3 dev [file.ai]                # dev loop, alias of run (browser)
  n3 studio [file.ai]             # inspect/debug in Studio

Quality
  n3 check [file.ai]              # static validation
  n3 fmt [file.ai]                # format app file
  n3 actions <file.ai> [--json]   # list actions (positional 'json' stays supported)
  n3 ui <file.ai>                 # print UI manifest

Ship
  n3 build [file.ai]              # build deployable bundle (alias: pack <file.ai>)
  n3 pack add <name[@version]>    # capability packs (contract)
  n3 clean                        # remove runtime artifacts

Advanced
  n3 preview [file.ai]            # production-like browser preview
  n3 start [file.ai]              # serve build artifacts
  n3 ship --to T --back           # promote build, alias promote/back
  n3 where [file.ai]              # show active target and build
  n3 proof <file.ai> --json       # write engine proof
  n3 verify <file.ai> --prod      # governance checks
  n3 when <file.ai> --json        # check spec compatibility
  n3 how | what | why | with      # explain the last run
  n3 lint <file.ai> [check]       # lint (strict tools via --strict-tools)
  n3 graph | exports <file.ai>    # dependency graph or exports (use --json)
  n3 data | persist <file.ai> ... # data status, reset, export, import
  n3 secrets | observe | explain  # secrets, observability, engine explain
  n3 memory | kit | exists        # memory recall, adoption kit, contract status
  n3 tools | packs | registry     # tool and pack management commands
  n3 pkg | pattern | test | eval  # packages, patterns, tests, evaluation
  n3 version | reserved | icons   # metadata and discovery
  n3 help                         # this help

Notes:
  file.ai is optional and defaults to ./app.ai when present
  if app.ai is missing: run `n3 <command> <file.ai>` or create app.ai
  legacy forms like `n3 run app.ai --target T --json` and `n3 actions app.ai json` remain supported
  Studio inspects; the browser renders the app
"""
    print(usage.strip())

def print_payload(payload: object, json_mode: bool) -> None:
    if json_mode:
        print(dumps_pretty(payload))
    else:
        print(format_plain(payload))

def print_version() -> None:
    print(f"namel3ss {get_version()}")
