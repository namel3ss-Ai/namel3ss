name: Bug report
description: Something is not working as expected
title: "[bug] "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thank you for helping improve namel3ss.
        Please keep reports focused and reproducible.

  - type: textarea
    id: snippet
    attributes:
      label: Minimal .ai snippet or attach the file
      description: Keep it as small as possible to reproduce.
    validations:
      required: true

  - type: textarea
    id: check-output
    attributes:
      label: Output of `n3 <app.ai> check`
      description: Paste the full command output.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected vs actual
      description: What you expected to happen, and what happened instead.
    validations:
      required: true

  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. n3 app.ai
        2. Click button "Run"
        3. Error appears
    validations:
      required: true

  - type: input
    id: os
    attributes:
      label: OS and Python version
      placeholder: "e.g., macOS 13, Python 3.11"
    validations:
      required: true
