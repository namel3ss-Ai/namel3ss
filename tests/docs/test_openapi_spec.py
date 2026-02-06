from __future__ import annotations

from namel3ss.docs.spec import build_openapi_spec
from tests.conftest import lower_ir_program


def test_openapi_spec_generation() -> None:
    source = """
record "User":
  id number
  name text

prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text

flow "summary_flow":
  ai:
    model is "gpt-4"
    prompt is "Summarise."
  return "ok"

flow "get_user":
  return "ok"

route "get_user":
  path is "/api/users/{id}"
  method is "GET"
  parameters:
    id is number
  request:
    id is number
  response:
    user is User
  flow is "get_user"
""".strip()
    program = lower_ir_program(source)
    spec = build_openapi_spec(program)
    expected = {
        "openapi": "3.0.3",
        "info": {"title": "namel3ss app", "version": "1.0"},
        "paths": {
            "/api/users/{id}": {
                "get": {
                    "operationId": "get_user",
                    "summary": "get_user",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "number"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"id": {"type": "number"}},
                                    "required": ["id"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Success.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"user": {"$ref": "#/components/schemas/User"}},
                                        "required": ["user"],
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Bad request.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
                            },
                        },
                        "500": {
                            "description": "Internal error.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
                            },
                        },
                    },
                    "x-flow": "get_user",
                    "x-generated": False,
                    "x-response-formats": ["json"],
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {"id": {"type": "number"}, "name": {"type": "string"}},
                    "required": ["id", "name"],
                },
                "ErrorEnvelope": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "remediation": {"type": "string"},
                    },
                    "required": ["code", "message", "remediation"],
                },
                "LLMCall": {
                    "type": "object",
                    "description": "LLM call metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_type": {"type": "string"},
                    },
                    "required": ["model", "prompt"],
                },
                "Summarise": {
                    "type": "object",
                    "description": "Summarise metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_type": {"type": "string"},
                    },
                    "required": ["model", "prompt"],
                },
                "RAG": {
                    "type": "object",
                    "description": "RAG metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_type": {"type": "string"},
                        "sources": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["model", "prompt", "sources"],
                },
                "Classification": {
                    "type": "object",
                    "description": "Classification metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_type": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["model", "prompt", "labels"],
                },
                "Translate": {
                    "type": "object",
                    "description": "Translate metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_type": {"type": "string"},
                        "source_language": {"type": "string"},
                        "target_language": {"type": "string"},
                    },
                    "required": ["model", "source_language", "target_language"],
                },
                "QA": {
                    "type": "object",
                    "description": "Question answering metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_fields": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["model", "output_fields"],
                },
                "COT": {
                    "type": "object",
                    "description": "Chain of thought metadata.",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "dataset": {"type": "string"},
                        "output_fields": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["model", "output_fields"],
                },
                "Chain": {
                    "type": "object",
                    "description": "Composable AI chain metadata.",
                    "properties": {
                        "steps": {"type": "array", "items": {"type": "object"}},
                        "output_fields": {"type": "array", "items": {"type": "string"}},
                        "tests": {"type": "object"},
                    },
                    "required": ["steps", "output_fields"],
                },
            }
        },
        "x-ai-flows": [
            {
                "name": "summarise",
                "kind": "llm_call",
                "model": "gpt-4",
                "prompt": "summary_prompt",
                "output_type": "text",
            },
            {
                "name": "summary_flow",
                "kind": "llm_call",
                "model": "gpt-4",
                "prompt": "Summarise.",
                "output_type": "text",
            },
        ],
    }
    assert spec == expected
