# Provider Capabilities

Provider selection stays explicit through model identifiers. No grammar changes are required.

## Provider Packs

Use namespaced model IDs in `ask ai`, for example:

```ai
ask ai:
  model: "huggingface:facebook/bart-large-cnn"
  user_input: article_text
```

For multimodal calls, use the existing mode-aware input syntax:

```ai
ask ai:
  mode: image
  model: "vision_gen:stable-diffusion"
  user_input: null
```

## Capability Tokens

Enable provider packs explicitly in `capabilities:`:

- `huggingface`
- `local_runner`
- `vision_gen`
- `speech`
- `third_party_apis`

If a flow uses a provider pack and the token is missing, compile-time validation fails with a guidance message.

## Runtime Matrix

| Provider | Capability token | Modes | Tools | Notes |
| --- | --- | --- | --- | --- |
| `mock` | n/a | text, image, audio | yes | Deterministic test double. |
| `openai` | n/a | text, image, audio | yes | Existing built-in provider. |
| `anthropic` | n/a | text, image | yes | Existing built-in provider. |
| `gemini` | n/a | text, image, audio | yes | Existing built-in provider. |
| `mistral` | n/a | text, image | yes | Existing built-in provider. |
| `ollama` | n/a | text | no | Existing local text provider. |
| `huggingface` | `huggingface` | text, image, audio | no | Deterministic provider-pack wrapper. |
| `local_runner` | `local_runner` | text | no | Deterministic local model runner pack. |
| `vision_gen` | `vision_gen` | image | no | Deterministic image generation with recorded seed. |
| `speech` | `speech` | audio | no | Deterministic transcription/synthesis behavior. |
| `third_party_apis` | `third_party_apis` | image, audio | no | Managed connectors with deterministic error/reporting contract. |

## Dependency Manager

Provider packs are available through the package index and install with:

- `n3 pkg add huggingface-pack`
- `n3 pkg add local-runner-pack`
- `n3 pkg add vision-gen-pack`
- `n3 pkg add speech-pack`
- `n3 pkg add third-party-apis-pack`

The resolved versions are written to `namel3ss.lock` for reproducible environments.

## Studio Configuration

Studio Setup includes a provider-pack section to:

- view installed provider packs and supported modes
- select default models per provider
- store provider secret names in `.namel3ss/provider_settings.json`

Secret values are never stored in this file. Store values through environment variables or the encrypted secrets workflow.

## Determinism Rules

- Provider/model selection is explicit via namespaced model IDs.
- Generative providers use fixed seeds by default; explicit seeds are honored and recorded.
- Provider outputs are normalized and deterministic for identical inputs in deterministic test mode.
- Missing secrets, unsupported models, and mode mismatches fail explicitly with deterministic errors.
