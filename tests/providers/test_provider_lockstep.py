from namel3ss.runtime.ai.providers import registry as provider_registry
from namel3ss.runtime.providers.capabilities import _CAPABILITIES
from namel3ss.runtime.tool_calls.provider_iface import get_provider_adapter


def _registry_ids() -> set[str]:
    return set(provider_registry._FACTORIES.keys())


def _capability_ids() -> set[str]:
    return set(_CAPABILITIES.keys())


def _tool_adapter_ids() -> set[str]:
    adapters: set[str] = set()
    for name, caps in _CAPABILITIES.items():
        if not caps.supports_tools:
            continue
        provider_stub = type("ProviderStub", (), {})()
        adapter = get_provider_adapter(name, provider_stub, model="dummy-model", system_prompt=None)
        if adapter:
            adapters.add(name)
    return adapters


def test_registry_and_capabilities_lockstep():
    assert _registry_ids() == _capability_ids()


def test_tool_capable_providers_have_adapters():
    adapters = _tool_adapter_ids()
    expected = {name for name, caps in _CAPABILITIES.items() if caps.supports_tools}
    assert adapters == expected
