# Advanced: Custom RAG Answer Flow

Use this when you want to replace the preset-generated answer routine with your own explicit flow.

```ai
spec is "1.0"
use preset "rag_chat":
  title is "Assistant"

override flow "rag.answer":
  let answer_out is call flow "rag.render_answer":
    input:
      question is input.message
      context is input.context
    output:
      answer_text
  return answer_out.answer_text

ai "rag_writer_ai":
  provider is "openai"
  model is "gpt-4o-mini"
  system_prompt is "You are a grounded RAG assistant. Return a professional plain-text response with exactly three sections in this order: Summary, Key Points, Recommendation. Use only grounded evidence from provided context. Every factual sentence must end with inline citation markers like [1], [2], [3]. Do not output JSON, YAML, code blocks, file paths, test filenames, or raw context dumps."
  memory:
    short_term is 0
    semantic is false
    profile is false

contract flow "rag.render_answer":
  input:
    question is text
    context is text
  output:
    answer_text is text

flow "rag.render_answer": requires true
  let answer_text is ""
  try:
    ask ai "rag_writer_ai" with structured input from map:
      "query" is "Answer this user question with this exact plain-text template and no extra sections:\nSummary:\n<2-3 sentences>\n\nKey Points:\n1. <one sentence>\n2. <one sentence>\n3. <one sentence>\n\nRecommendation:\n<one sentence>\n\nRules: use only provided context, keep wording concise and professional, end factual lines with [1], [2], [3] citations, never output raw context, file paths, URLs, internal filenames, JSON, or markdown tables.\n\nQuestion: " + input.question
      "context" is input.context
    as model_answer
    if model_answer is "":
      set answer_text is "Summary:\nGrounded evidence was found for this question [1]. A synthesized response is temporarily unavailable, but the source evidence is indexed and accessible [1].\n\nKey Points:\n1. Relevant support exists in the indexed sources [1].\n2. Open View Sources to verify exact snippets and provenance [1].\n3. Retry once synthesis is available to receive a fuller narrative [1].\n\nRecommendation:\nReview the cited evidence now and rerun the same question after provider recovery [1]."
    else:
      set answer_text is model_answer
  with catch err:
    if input.context is "":
      set answer_text is "No grounded support found in indexed sources for this query."
    else:
      set answer_text is "Summary:\nGrounded evidence was found for this question [1]. AI synthesis is currently unavailable in this runtime [1].\n\nKey Points:\n1. The indexed context contains supporting information [1].\n2. View Sources remains available for direct evidence review [1].\n3. Provider credentials are required for synthesized answers [1].\n\nRecommendation:\nSet NAMEL3SS_OPENAI_API_KEY, rerun the app, and ask again for a fully composed response [1]."
  return map:
    "answer_text" is answer_text
```

Use `n3 expand app.ai` to inspect the final generated program and compare this explicit version with preset-generated output.
