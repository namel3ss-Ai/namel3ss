name: Design feedback
description: Discuss design or UX aspects
title: "[design] "
labels: ["discussion"]
body:
  - type: textarea
    id: snippet
    attributes:
      label: Relevant .ai snippet or screenshot
      description: Include the smallest example or a Studio screenshot.

  - type: textarea
    id: check-output
    attributes:
      label: Output of `n3 <app.ai> check` (if relevant)

  - type: textarea
    id: goal
    attributes:
      label: What are you trying to achieve?
    validations:
      required: true

  - type: textarea
    id: feedback
    attributes:
      label: Feedback / concerns
    validations:
      required: true

  - type: input
    id: os
    attributes:
      label: OS and Python version
