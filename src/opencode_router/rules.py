"""Role-pattern → bucket assignment rules.

Default rules cover obvious general-purpose patterns. Users can override
or extend by writing their own rules file at the path in
`~/.config/opencode/orchestration-rules.json`. Schema:

    {
      "rules": [
        ["<substring pattern>", "<bucket>"],
        ...
      ],
      "default_bucket": "pro"
    }

First match wins, so put specific patterns BEFORE general ones. Patterns
are matched against `<agent name> <description>` lowercased.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .paths import RULES_FILE

# Generic, role-shape rules. Deliberately small — domain-specific rules
# (Chinese platforms, civil engineering, narrative-vs-UI designers, etc.)
# are project-specific and belong in the user's rules file.
DEFAULT_RULES: list[tuple[str, str]] = [
    # Security-specific FIRST — must beat generic "reviewer" / "engineer"
    ("security-engineer", "pro"),
    ("security-auditor", "pro"),
    ("security-reviewer", "pro"),
    ("penetration-tester", "pro"),
    ("compliance-auditor", "pro"),
    ("threat-detection", "pro"),

    # Code review / debug / QA → flash (must beat "engineer")
    ("reviewer", "flash"),
    ("debugger", "flash"),
    ("error-detective", "flash"),
    ("error-resolver", "flash"),
    ("build-error", "flash"),
    ("qa-automation", "flash"),
    ("test-architect", "flash"),
    ("api-tester", "flash"),

    # Visual / UI / UX → visual (specific, beats "designer" if anyone uses that)
    ("ui-designer", "visual"),
    ("ux-architect", "visual"),
    ("ux-researcher", "visual"),
    ("brand-guardian", "visual"),
    ("visual-storyteller", "visual"),
    ("technical-artist", "visual"),
    ("level-designer", "visual"),

    # Translation → translation
    ("language-translator", "translation"),
    ("localization", "translation"),
    ("cultural-intelligence", "translation"),

    # Sales/customer/support → flash (must beat "engineer" e.g. sales-engineer)
    ("sales-engineer", "flash"),
    ("sales-coach", "flash"),
    ("customer-service", "flash"),
    ("customer-success", "flash"),
    ("support-responder", "flash"),
    ("outreach", "flash"),
    ("hr-onboarding", "flash"),

    # Engineering / coding → coding (broad — keep AFTER reviewer/security/sales)
    ("architect", "coding"),
    ("engineer", "coding"),
    ("developer", "coding"),
    ("scripter", "coding"),
    ("fullstack", "coding"),
    ("backend", "coding"),
    ("frontend", "coding"),
    ("mobile", "coding"),
    ("embedded", "coding"),
    ("blockchain", "coding"),
    ("devops", "coding"),
    ("sre", "coding"),
    ("kubernetes", "coding"),
    ("terraform", "coding"),
    ("data-engineer", "coding"),
    ("ml-engineer", "coding"),
    ("ai-engineer", "coding"),
    ("mlops", "coding"),
    ("nlp-engineer", "coding"),
    ("cli-developer", "coding"),
    ("api-designer", "coding"),
    ("graphql", "coding"),
    ("microservices", "coding"),
    ("solidity", "coding"),
    ("game-developer", "coding"),
    ("rapid-prototyper", "coding"),
    ("senior-developer", "coding"),

    # Documentation → flash
    ("technical-writer", "flash"),
    ("documentation-engineer", "flash"),
    ("api-documentation", "flash"),

    # Content / writing / strategy / analysis → pro
    ("content-creator", "pro"),
    ("content-strategist", "pro"),
    ("blog", "pro"),
    ("copywriter", "pro"),
    ("narrative-designer", "pro"),
    ("game-designer", "pro"),
    ("strategist", "pro"),
    ("product-manager", "pro"),
    ("project-manager", "pro"),
    ("scrum-master", "pro"),
    ("research-analyst", "pro"),
    ("market-researcher", "pro"),
    ("data-scientist", "pro"),
    ("financial-analyst", "pro"),
    ("legal-advisor", "pro"),
    ("trend-analyst", "pro"),

    # Last-resort role catch-alls (loose)
    ("reviewer", "flash"),
    ("auditor", "pro"),
    ("analyst", "pro"),
    ("researcher", "pro"),
    ("writer", "pro"),
    ("planner", "pro"),
    ("manager", "pro"),
    ("designer", "visual"),
]

DEFAULT_BUCKET = "pro"


@dataclass(frozen=True)
class RuleSet:
    rules: list[tuple[str, str]]
    default_bucket: str

    def pick(self, name: str, description: str) -> str:
        text = f"{name} {description}".lower()
        for pattern, bucket in self.rules:
            if pattern in text:
                return bucket
        return self.default_bucket


def load() -> RuleSet:
    """Load user rules if present, otherwise return the defaults.

    The user file may set `"mode": "extend"` to PREPEND user rules
    before the built-in defaults — useful for one-off overrides without
    copying the whole default ruleset. Default mode is "replace".
    """
    if not RULES_FILE.exists():
        return RuleSet(rules=list(DEFAULT_RULES), default_bucket=DEFAULT_BUCKET)
    data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    rules_raw = data.get("rules", [])
    user_rules: list[tuple[str, str]] = []
    for item in rules_raw:
        if isinstance(item, list) and len(item) == 2:
            user_rules.append((str(item[0]), str(item[1])))

    mode = str(data.get("mode", "replace")).lower()
    default_bucket = str(data.get("default_bucket", DEFAULT_BUCKET))

    if mode == "extend":
        # User rules win because they're checked first.
        return RuleSet(
            rules=user_rules + list(DEFAULT_RULES),
            default_bucket=default_bucket,
        )
    return RuleSet(
        rules=user_rules or list(DEFAULT_RULES),
        default_bucket=default_bucket,
    )
