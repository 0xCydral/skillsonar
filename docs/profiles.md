# Provider profiles

A profile maps abstract role buckets to concrete model paths. Switching
profiles re-routes every agent to a new provider in one command.

## Why profiles

Production agentic setups draw on multiple providers — coding plans,
embedding APIs, image-capable models, regional plans. Hardcoding model
paths in every agent definition makes it brittle: a plan rolls over,
quota runs out, a new model ships, and you're sed-ing through 200
files.

The profile abstraction:

```
agent description ──► routing rule ──► bucket ──► profile ──► model path
        (text)        (substring)      (label)    (active)    (provider/id)
```

Only the profile changes when you swap providers. Rules and agents stay
untouched.

## Schema

```jsonc
{
  "active": "<one of the keys in profiles>",
  "profiles": {
    "<profile name>": {
      "description": "Plain-English summary of when to use this profile.",
      "buckets": {
        "pro":         "<provider/model>",
        "flash":       "<provider/model>",
        "coding":      "<provider/model>",
        "visual":      "<provider/model>",
        "chinese":     "<provider/model>",
        "translation": "<provider/model>"
      }
    }
  }
}
```

- `pro` is the only required bucket. Missing buckets fall back to it.
- Profile names are arbitrary — pick what's meaningful.

## CLI

```bash
opencode-router profile list             # all profiles, marks active
opencode-router profile current          # show active + bucket map
opencode-router profile show <name>      # show one profile
opencode-router profile set <name>       # switch + auto re-apply
opencode-router profile set <name> --no-apply   # switch without re-applying
```

`set` is the workhorse — it switches the active profile AND re-runs
`models apply`, so every agent's model field updates in one shot.

## Bucket conventions

The default rules engine recognises these buckets:

| Bucket | Typical roles |
|---|---|
| `pro` | Heavy reasoning, writing, strategy, security audits, default |
| `flash` | Code review, debugging, customer support, the router itself |
| `coding` | Architects, engineers, developers, scripters |
| `visual` | UI/UX, design, brand, level designers, image work |
| `chinese` | Chinese consumer-platform agents |
| `translation` | Translation, localization, cultural-cross |

You can use different bucket names — just keep the keys consistent
between your profile file and your rules file.

## Picking models for each bucket

| Bucket | What to look for | Example |
|---|---|---|
| `pro` | Strong reasoning, large context, decent writing | DeepSeek V4 Pro, Claude Sonnet, GPT-4 |
| `flash` | Fast, cheap, "good enough" | DeepSeek V4 Flash, Haiku, GPT-4o-mini |
| `coding` | Code-specialised | Kimi for Coding, Qwen3-Coder, Codex |
| `visual` | Vision-language model | Qwen3-VL, GPT-4o (vision), Mimo Pro |
| `chinese` | Native Chinese training | GLM-5.1, Qwen, Yi |
| `translation` | Multilingual | Qwen3.5, Aya, GPT-4 |

Don't sweat it — start with one model for everything, refine later.

## Examples shipped

See `examples/profiles/starter-profile.json` for four worked examples:

- `ollama-local` — everything self-hosted, no external API
- `ollama-cloud` — all six buckets on Ollama Cloud
- `nvidia-nim` — NVIDIA NIM credits
- `deepseek-official` — official DeepSeek API for pro/flash

Copy, edit, save as `~/.config/opencode/orchestration-profile.json`.
