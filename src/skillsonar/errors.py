"""The errors the CLI turns into a one-line message instead of a traceback."""


class SkillsonarError(Exception):
    """Base for every error skillsonar reports to the user."""


class SkillIndexError(SkillsonarError):
    """The index is missing, unreadable or out of date."""


class OllamaError(SkillsonarError):
    """The embeddings service failed or is unreachable."""


class RerankError(SkillsonarError):
    """The rerank service failed, is unreachable or is not configured."""
