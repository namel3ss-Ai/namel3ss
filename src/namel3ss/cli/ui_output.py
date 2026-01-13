from __future__ import annotations

from namel3ss.cli.json_io import dumps_pretty
from namel3ss.traces.plain import format_plain
from namel3ss.version import get_version

def print_usage() -> None:
    usage = """Usage:
  n3 new template name            # scaffold project, omit args to list
  n3 init template name           # scaffold project (alias for new)
  n3 version                      # show installed version
  n3 status                       # show .namel3ss runtime artifact status
  n3 clean                        # delete .namel3ss artifacts (with confirmation)
  n3 run app.ai --target T --json # run app
  n3 pack app.ai --target T       # build artifacts, alias build
  n3 ship --to T --back           # promote build, alias promote, rollback alias back
  n3 where app.ai                 # show active target and build
  n3 proof app.ai --json          # write engine proof
  n3 memory text                  # recall memory
  n3 memory why                   # explain last recall
  n3 memory show                  # show last recall details
  n3 memory @assistant text       # recall with named AI profile
  n3 verify app.ai --prod --json  # governance checks
  n3 verify --dx --json           # DX promise gate (repo)
  n3 release-check --json report.json # release Go/No-Go gate
  n3 expr-check --json report.json    # expression surface gate
  n3 readability path --json report.json --txt report.txt # grammar readability report
  n3 eval --json eval_report.json     # evaluation gate
  n3 secrets app.ai               # secret status and audit, subcommands status audit
  n3 observe app.ai --since T --json # engine observability stream
  n3 explain app.ai --json        # explain engine state
  n3 why app.ai --json            # explain the app
  n3 how                          # explain last run
  n3 with                         # explain tool usage and blocks from last run
  n3 what                         # show last run outcome
  n3 when app.ai --json           # check spec compatibility
  n3 see                          # explain last UI manifest
  n3 fix --json                   # show last runtime error summary
  n3 exists app.ai --json         # contract summary, uses .namel3ss contract last when present
  n3 kit app.ai --format md       # adoption kit summary, writes .namel3ss kit
  n3 editor app.ai --port N       # start editor service
  n3 check app.ai                 # validate, alias n3 app.ai check
  n3 ui app.ai                    # print UI manifest
  n3 actions app.ai json          # list actions
  n3 studio app.ai --port N       # start Studio viewer, use --dry to skip server in tests
  n3 fmt app.ai check             # format in place, alias format
  n3 lint app.ai check            # lint, use --strict-tools for tool warnings
  n3 graph app.ai --json          # module dependency graph
  n3 exports app.ai --json        # module export list
  n3 data app.ai command          # data store status and reset, alias persist
  n3 migrate app.ai --to 1.0      # migrate spec versions deterministically
  n3 deps command --json          # python env and deps status install sync lock clean
  n3 tools command --json         # tool bindings status list search bind unbind format
  n3 packs command --json         # tool packs add init validate review bundle sign status verify enable
  n3 registry command --json      # registry index add build
  n3 discover phrase --json       # discover packs by intent
  n3 pkg command --json           # packages search info add validate install
  n3 pattern command --json       # patterns list new verify run
  n3 app.ai --json                # run default flow
  n3 app.ai action_id payload --json # execute UI action, payload optional
  n3 help                         # this help
  Aliases and legacy: build, promote, persist, format, pkg
  Notes:
    app.ai is optional and defaults to app.ai in the current folder (or nearest parent)
    use --app or --project to override discovery
    flags are optional unless stated
    actions uses json for JSON output
"""
    print(usage.strip())

def print_payload(payload: object, json_mode: bool) -> None:
    if json_mode:
        print(dumps_pretty(payload))
    else:
        print(format_plain(payload))

def print_version() -> None:
    print(f"namel3ss {get_version()}")
