# Creating agents

An agent is a Markdown file with YAML frontmatter. The frontmatter
declares metadata; the body is the agent's system prompt.

## Minimum viable agent

```markdown
---
description: One-paragraph description of what this agent does.
mode: subagent
---

# Agent Name

You are an X. Your job is to Y. Do A, B, C. Avoid D and E.
```

That's it. Save as `~/.config/opencode/agents/<name>.md`. Run
`opencode-router init`. Done.

## Frontmatter fields

| Field | Required | Purpose |
|---|---|---|
| `description` | Yes | Used for routing. Embed-able. Should match the kind of *task* the agent handles, not just the agent's title. |
| `mode` | No (default `subagent`) | `primary` for entry-point agents (the router), `subagent` for everything dispatchable, `all` for both. |
| `name` | No | Display name (humanized filename used if absent). |
| `color` | No | TUI accent colour. |

The router's index **excludes** any agent with `mode: primary` so it
won't recommend itself.

## Writing good descriptions

The description is the only thing the embedding model sees. Make it
**task-shaped**, not biography:

```yaml
# Bad — title and brag, no task signal
description: World-class senior engineer with 30 years of experience.

# Good — names the work, the domain, the deliverable
description: Reviews TypeScript and JavaScript code for type safety, async correctness, security gaps, and idiomatic patterns. Returns structured findings categorised by severity.
```

Rules of thumb:

- Lead with a verb: *"Reviews"*, *"Writes"*, *"Designs"*, *"Audits"*.
- Name the domain: *"TypeScript"*, *"PostgreSQL"*, *"Docker"*.
- Name the deliverable: *"structured findings"*, *"refactor patches"*,
  *"design doc"*.
- 1-3 sentences. Don't pad to look thorough.

## System prompt body

The Markdown body becomes the agent's system prompt at runtime. Treat
it like any other system prompt:

- State the agent's identity and scope.
- Give explicit rules and a definition of done.
- List things to avoid.
- Don't invent capabilities the agent doesn't have.

## Importing existing collections

Many open-source agent collections exist. Most are drop-in compatible
because the `.md` + frontmatter format is widespread.

```bash
# agency-agents
git clone https://github.com/msitarzewski/agency-agents
cp -r agency-agents/agents/*.md ~/.config/opencode/agents/

# Then re-init
opencode-router init
```

Watch for legacy `model: opus|sonnet|haiku` shorthands in older
collections — `opencode-router` ignores the frontmatter `model` field
(it sets the model itself based on rules + profile), so you can leave
those in place. They have no effect on dispatch.

## Iterating

The fastest debug loop:

```bash
$EDITOR ~/.config/opencode/agents/my-agent.md
opencode-router index build           # if you changed the description
opencode-router route "<test query>"  # see what the router picks
```

You don't need to restart OpenCode between agent edits — the prompt
file is loaded fresh on every dispatch.
