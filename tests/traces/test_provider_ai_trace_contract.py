from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.ai.providers import registry as provider_registry
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE_TEMPLATE = '''{capabilities_block}

ai "assistant":
  provider is "{provider}"
  model is "{model}"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''

MODEL_BY_PROVIDER = {
    "huggingface": "huggingface:bert-base-uncased",
    "local_runner": "local_runner:llama3-8b-q4",
    "vision_gen": "vision_gen:stable-diffusion",
    "speech": "speech:whisper-base",
    "third_party_apis": "third_party_apis:aws-rekognition-labels",
}


def _program_source(provider: str) -> str:
    capability_tokens = {
        "huggingface",
        "local_runner",
        "vision_gen",
        "speech",
        "third_party_apis",
    }
    capability_block = ""
    if provider in capability_tokens:
        capability_block = f'capabilities:\n  {provider}\n'
    model = MODEL_BY_PROVIDER.get(provider, "test-model")
    return SOURCE_TEMPLATE.format(
        capabilities_block=capability_block,
        provider=provider,
        model=model,
    )


class StubProvider:
    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        return AIResponse(output=f"[{model}] ok")


def test_text_only_traces_for_all_providers(monkeypatch):
    provider_ids = set(provider_registry._FACTORIES.keys())
    for name in provider_ids:
        program = lower_ir_program(_program_source(name))
        monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda _name, _cfg: StubProvider())
        result = execute_flow(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            initial_state={},
            ai_profiles=program.ais,
        )
        trace = result.traces[0]
        events = trace.canonical_events
        types = [event["type"] for event in events]
        assert types[0] == "memory_recall"
        assert "memory_write" in types
        assert "ai_call_started" in types
        assert types[-1] in {
            "memory_write",
            "memory_denied",
            "memory_forget",
            "memory_conflict",
            "memory_border_check",
            "memory_promoted",
            "memory_promotion_denied",
            "memory_phase_started",
            "memory_deleted",
            "memory_phase_diff",
            "memory_team_summary",
            "memory_explanation",
            "memory_links",
            "memory_path",
            "memory_impact",
            "memory_change_preview",
            "memory_proposed",
            "memory_approved",
            "memory_rejected",
            "memory_agreement_summary",
            "memory_trust_check",
            "memory_approval_recorded",
            "memory_trust_rules",
            "memory_rule_applied",
            "memory_rules_snapshot",
            "memory_rule_changed",
            "memory_handoff_created",
            "memory_handoff_applied",
            "memory_handoff_rejected",
            "memory_agent_briefing",
            "ai_call_completed",
            "ai_call_failed",
        }
        assert types.index("ai_call_started") > types.index("memory_recall")
        for event in events:
            assert "trace_version" in event
        for event in events:
            if "call_id" in event:
                assert event["provider"] == name
                assert "call_id" in event
