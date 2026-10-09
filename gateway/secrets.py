"""Resolution of secret references used in policy files."""


def resolve(ref: str) -> str:
    """Resolve a reference of the form "ref:NAME" to the value of env var NAME.

    Must: raise ValueError for strings without the "ref:" prefix and a clear error if the
    variable is unset. Resolved values must never be logged or audited.
    """
    raise NotImplementedError
