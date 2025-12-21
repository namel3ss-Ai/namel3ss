title: "Help / Q&A: <question>"
labels: ["question"]
body:
  - type: markdown
    attributes:
      value: "Ask usage or behavior questions."
  - type: textarea
    id: question
    attributes:
      label: Question
      description: Be specific about what you’re trying to do.
    validations:
      required: true
  - type: textarea
    id: snippet
    attributes:
      label: Minimal .ai snippet (if applicable)
  - type: textarea
    id: check
    attributes:
      label: Output of `n3 <app.ai> check` (if relevant)
