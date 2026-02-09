# Icons and Tones

What it checks: tone usage in stories and icon semantics across the app.

## Warnings
- `story.tone_missing_icon` - a non-neutral tone has no icon.
- `story.icon_tone_mismatch` - icon does not match the tone.
- `story.tone_overuse` - every step uses a non-neutral tone.
- `icon.misuse` - an icon is used on a neutral step.
- `icon.inconsistent_semantics` - the same tone uses different icons across pages.
- `icon.overuse` - too many icons in one story.

## Fix
Reserve tones and icons for signal. Use one icon per tone.

## Example
```ai
page "resolution":
  story "Resolution":
    step "Acknowledge":
      text is "Confirm receipt and set expectations."
    step "Resolve":
      tone is "success"
      icon is check
      text is "Summarize the outcome and next step."
```
