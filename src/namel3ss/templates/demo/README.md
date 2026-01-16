# {{PROJECT_NAME}}

template
- {{TEMPLATE_NAME}} v{{TEMPLATE_VERSION}}

60-second run
- n3 run
- or: n3 app.ai

what this shows
- prompt and answer records
- explicit ai boundary with mock provider/model by default
- why/explain fields stored with each answer
- media + story intent alongside chat

ai provider (optional)
- default uses mock
- to use openai, set N3_DEMO_PROVIDER=openai and NAMEL3SS_OPENAI_API_KEY

project structure
- app.ai
- media/ (welcome.svg)
- .namel3ss/ (runtime artifacts)

notes
- ui manifest output is available via `n3 app.ai ui`
