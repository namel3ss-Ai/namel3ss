# Multi-Modal Support

namel3ss supports image and audio inputs in `ask ai` and `run agent` statements with deterministic preprocessing and explicit capability gates.

## Enable capabilities

```ai
capabilities:
  vision
  speech
```

- `vision` is required for `image` mode.
- `speech` is required for `audio` mode.
- If these are missing, compilation fails with an explicit capability error.

## Grammar

Existing text mode is unchanged.

```ai
ask ai "assistant" with input: "hello" as reply
```

Block-form examples:

```ai
ask ai:
  mode: image
  model: "vision-model-id"
  user_input: state.image_path
```

```ai
ask ai:
  mode: audio
  model: "speech-model-id"
  user_input: state.audio_path
```

Image and audio modes are explicit:

```ai
ask ai "assistant" with image input: state.image_path as image_reply
ask ai "assistant" with audio input: state.audio_path as audio_reply
```

`run agent` supports the same mode syntax:

```ai
run agent "planner" with image input: state.photo as result
run agent "scribe" with audio input: state.voice_note as transcript
```

## Input contract

For image and audio modes, the input value may be:
- A local file path
- An `http`/`https` URL
- A state value that resolves to one of the above
- Raw bytes

Optional seed:
- pass a map with `source` and `seed`
- if omitted, seed is derived deterministically from input hash

Example:

```ai
ask ai "assistant" with image input: state.image_path as result
```

or via a map state value:

```json
{"source": "media/photo.png", "seed": 42}
```

## Response contract

`AIResponse` now allows multimodal fields while remaining backward compatible:
- `output`
- `image_id`
- `image_url`
- `description`
- `transcript`
- `audio_url`

Runtime still writes text output into flow variables, with fallback order:
- `output`
- `transcript`
- `description`
- media URL/id when text is absent

## Determinism

- The same local file bytes produce the same canonical input payload and hash.
- The same URL produces the same canonical payload and derived seed.
- If no seed is provided, the runtime derives one from the input hash.
- Flow step order is unchanged; multimodal processing is sequential.
- Content filters are deterministic string checks.

## Error behaviour

- Missing capability (`vision`/`speech`) fails at compile time.
- Provider with no declared modality support fails at compile time.
- Missing local files fail at runtime with path-specific errors.
- Unsupported file extensions fail with explicit allowed extension lists.
- Decoding failures raise explicit image/audio decode errors.
- Content filter failures raise deterministic policy errors.

## UI rendering

Studio UI renderer supports:
- `type: "image"` (existing)
- `type: "audio"` (new), with native audio controls and optional transcript text
