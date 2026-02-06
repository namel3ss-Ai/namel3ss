from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(APP_SOURCE, encoding="utf-8")
    return app


def test_cli_tenant_federation_and_cluster_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli_main(
        ["tenant", "add", "acme", "ACME Corp", "acme_", "local", "--quota", "max_flows=100", "--json"]
    ) == 0
    tenant_add = json.loads(capsys.readouterr().out)
    assert tenant_add["ok"] is True
    assert tenant_add["tenant"]["tenant_id"] == "acme"
    assert tenant_add["tenant"]["resource_quotas"]["max_flows"] == 100.0

    assert cli_main(["tenant", "set-current", "acme", "--json"]) == 0
    tenant_current = json.loads(capsys.readouterr().out)
    assert tenant_current["ok"] is True
    assert tenant_current["tenant_id"] == "acme"

    assert cli_main(["tenant", "list", "--json"]) == 0
    tenant_list = json.loads(capsys.readouterr().out)
    assert tenant_list["ok"] is True
    assert tenant_list["count"] == 1
    assert tenant_list["tenants"][0]["tenant_id"] == "acme"
    assert tenant_list["tenants"][0]["is_current"] is True

    assert cli_main(
        [
            "federation",
            "add-contract",
            "acme",
            "beta",
            "get_customer_info",
            "--input",
            "customer_id:number",
            "--output",
            "info:text",
            "--auth",
            "client_id=acme_beta_client",
            "--rate-limit",
            "60",
            "--json",
        ]
    ) == 0
    contract_add = json.loads(capsys.readouterr().out)
    assert contract_add["ok"] is True
    assert contract_add["contract"]["source_tenant"] == "acme"
    assert contract_add["contract"]["target_tenant"] == "beta"
    assert contract_add["contract"]["flow_name"] == "get_customer_info"
    assert contract_add["contract"]["rate_limit"]["calls_per_minute"] == 60

    assert cli_main(["federation", "list", "--json"]) == 0
    contract_list = json.loads(capsys.readouterr().out)
    assert contract_list["ok"] is True
    assert contract_list["count"] == 1

    assert cli_main(["federation", "remove-contract", "acme", "beta", "get_customer_info", "--json"]) == 0
    contract_remove = json.loads(capsys.readouterr().out)
    assert contract_remove["ok"] is True

    (tmp_path / "cluster.yaml").write_text(
        (
            "cluster:\n"
            "  nodes:\n"
            "    - name: node1\n"
            "      host: 10.0.0.1\n"
            "      role: controller\n"
            "      capacity: 4cores-8GB\n"
            "    - name: node2\n"
            "      host: 10.0.0.2\n"
            "      role: worker\n"
            "      capacity: 4cores-8GB\n"
            "  scaling_policy:\n"
            "    target_cpu_percent: 70\n"
            "    max_nodes: 5\n"
            "    min_nodes: 1\n"
            "  rolling_update:\n"
            "    max_unavailable: 1\n"
        ),
        encoding="utf-8",
    )

    assert cli_main(["cluster", "status", "--json"]) == 0
    status_before = json.loads(capsys.readouterr().out)
    assert status_before["ok"] is True
    assert status_before["active_nodes"] >= 1

    assert cli_main(["cluster", "scale", "95", "--json"]) == 0
    scaled = json.loads(capsys.readouterr().out)
    assert scaled["ok"] is True
    assert scaled["action"] in {"scale_up", "hold"}

    assert cli_main(["cluster", "deploy", "1.2.0", "--json"]) == 0
    deployed = json.loads(capsys.readouterr().out)
    assert deployed["ok"] is True
    assert deployed["deployed_version"] == "1.2.0"
    assert len(deployed["rollout_steps"]) >= 1
