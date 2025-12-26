# auth-basic

Basic identity helpers and require-style flows for small apps.

## Install

```
n3 pkg add github:namel3ss-ai/auth-basic@v0.1.0
```

## Usage

```
use "auth-basic" as auth

page "home":
  button "Set demo user":
    calls flow "auth.set_user"
```

## Development

```
n3 pkg validate .
n3 test
n3 verify --prod
```
