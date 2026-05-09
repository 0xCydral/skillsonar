# Routing rules

Rules map an agent's name + description to a bucket. The bucket then
maps to a concrete model via the active profile. Rules are checked in
order — **first match wins** — so specific patterns must come before
general ones.

## Defaults

Built-in defaults live in `src/opencode_router/rules.py` (`DEFAULT_RULES`).
They cover obvious patterns:

- `reviewer` / `auditor` / `debugger` → `flash`
- `security-engineer` / `penetration-tester` → `pro`
- `architect` / `engineer` / `developer` → `coding`
- `ui-designer` / `ux-architect` → `visual`
- `language-translator` / `localization` → `translation`
- `writer` / `strategist` / `analyst` → `pro`

The default rules are intentionally minimal. Domain-specific patterns
(Chinese consumer platforms, civil engineering vs software engineering,
narrative-designer-not-UI-designer) are project-specific and belong in
your rules file.

## Override / extend

Write `~/.config/opencode/orchestration-rules.json`:

```jsonc
{
  "rules": [
    ["security-reviewer",     "pro"],
    ["sales-engineer",        "flash"],
    ["my-internal-agent",     "coding"],
    ["douyin-strategist",     "chinese"],
    ["narrative-designer",    "pro"],
    ["civil-engineer",        "pro"]
  ],
  "default_bucket": "pro"
}
```

When this file exists, **it replaces** the built-in defaults entirely.
If you only want to add to the defaults, copy the defaults out of
`rules.py` and prepend your custom rules.

## Patterns

- Plain substring match against `lowercase(<name> + " " + <description>)`.
- No regex, no wildcards. Keep it simple.
- Order: specific → general. `security-reviewer` MUST come before
  `reviewer`, otherwise `reviewer` wins and security agents go to
  `flash` instead of `pro`.
- Match agents the way they actually appear. Look at your agent's
  filename and description before writing a rule.

## Testing rules

```bash
opencode-router models apply --profile <name>
```

This rebuilds every agent's model assignment using your current rules
+ a chosen profile. The output shows bucket distribution and per-model
counts. Spot-check that obvious agents land in the right buckets.

For interactive testing without writing to `opencode.json`, the
recommended approach is `opencode-router doctor` followed by
`opencode-router route "<test query>"` — the latter shows the agent
that *would* be picked.

## Adding a new bucket

If your taxonomy needs a bucket the defaults don't have (e.g.
`legal`, `finance`, `creative-writing`):

1. Add the bucket to your profile file:

   ```json
   "buckets": {
     "pro":   "...",
     "flash": "...",
     "legal": "deepseek/deepseek-v4-pro",
     ...
   }
   ```

2. Add rules pointing at it:

   ```json
   ["legal-advisor",   "legal"],
   ["legal-reviewer",  "legal"]
   ```

3. Re-apply: `opencode-router models apply`.

The bucket name is just a label — it doesn't have to match anything
the package knows about. As long as the same string appears as a
profile bucket key AND as the right-hand side of one or more rules,
it's wired up.
