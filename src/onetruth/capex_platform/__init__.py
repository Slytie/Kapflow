"""CAPEX platform extension points."""

from onetruth.capex_platform.project_access import (
    AuthorizedProject,
    AuthorizedProjectsQuery,
    AuthorizedProjectsResult,
)

__all__ = [
    "AuthorizedProject",
    "AuthorizedProjectsQuery",
    "AuthorizedProjectsResult",
]
