name: Feature request
description: Propose or discuss a feature
title: "[idea] "
labels: ["discussion"]
body:
  - type: textarea
    id: snippet
    attributes:
      label: Minimal .ai snippet (if applicable)
      description: Show how you would use the feature.

  - type: textarea
    id: check-output
    attributes:
      label: Output of `n3 <app.ai> check` (if you have a snippet)

  - type: textarea
    id: problem
    attributes:
      label: What problem are you trying to solve?
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Desired behavior
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: How do you solve this today?
