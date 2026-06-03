from __future__ import annotations

from onetruth.application.services.logistics_workpage_action_registry import (
    LOGISTICS_WORKPAGE_ACTION_PACK,
)
from onetruth.application.services.workpage_action_registry import WorkpageActionRegistry


DEFAULT_WORKPAGE_ACTION_REGISTRY = WorkpageActionRegistry(
    (LOGISTICS_WORKPAGE_ACTION_PACK,)
)
