# Service Environment Example

This example shows explicit environment configuration and a service start.

1) Create a config source:

```
# .env
N3_PERSIST_TARGET=postgres
N3_DATABASE_URL=postgres://...
NAMEL3SS_OPENAI_API_KEY="..."
```

2) Build a service snapshot:

```
n3 pack --target service
```

3) Promote the build:

```
n3 ship --to service
```

4) Start the service:

```
n3 start --target service
```

Studio shows the environment summary, active build, and deployment state under the Deploy tab.
