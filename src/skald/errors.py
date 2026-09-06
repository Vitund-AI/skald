"""Error types shared by the CLI and the HTTP server."""


class SkaldError(Exception):
    """Base error. ``exit_code`` is used by the CLI, ``http_status`` by the server."""

    exit_code = 1
    http_status = 400


class NotFoundError(SkaldError):
    http_status = 404


class CorruptStoryError(SkaldError):
    exit_code = 2
    http_status = 422


class ConfigError(SkaldError):
    exit_code = 2
    http_status = 500


class ConflictError(SkaldError):
    http_status = 409


class GitError(SkaldError):
    http_status = 500
