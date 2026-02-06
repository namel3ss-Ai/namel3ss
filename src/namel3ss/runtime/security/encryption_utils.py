from __future__ import annotations

from namel3ss.security_encryption import EncryptionService


def encrypt_value(service: EncryptionService, value: object) -> dict:
    token = service.encrypt_json(value)
    return service.wrap_encrypted(token)


def decrypt_value(service: EncryptionService, value: object) -> object:
    token = service.unwrap_encrypted(value)
    if token is None:
        return value
    return service.decrypt_json(token)


def encrypt_run_payload(payload: dict, service: EncryptionService) -> dict:
    result = dict(payload)
    for key in ("state", "result", "traces"):
        if key in result:
            result[key] = encrypt_value(service, result[key])
    contract = result.get("contract")
    if isinstance(contract, dict):
        contract_copy = dict(contract)
        for key in ("state", "result", "traces"):
            if key in contract_copy:
                contract_copy[key] = encrypt_value(service, contract_copy[key])
        result["contract"] = contract_copy
    return result


def encrypt_execution_pack(pack: dict, service: EncryptionService) -> dict:
    result = dict(pack)
    for key in ("execution_steps", "traces", "error"):
        if key in result:
            result[key] = encrypt_value(service, result[key])
    return result


def encrypt_ai_record(record: dict, service: EncryptionService) -> dict:
    result = dict(record)
    for key in ("output", "expected"):
        if key in result:
            result[key] = encrypt_value(service, result[key])
    return result


def encrypt_prompt_entry(entry: dict, service: EncryptionService) -> dict:
    result = dict(entry)
    if "prompt" in result:
        result["prompt"] = encrypt_value(service, result["prompt"])
    return result


__all__ = [
    "decrypt_value",
    "encrypt_ai_record",
    "encrypt_execution_pack",
    "encrypt_prompt_entry",
    "encrypt_run_payload",
    "encrypt_value",
]
