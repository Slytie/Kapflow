from __future__ import annotations

from onetruth.application.services.logistics_workpage_descriptors import (
    LOGISTICS_WORKPAGE_DESCRIPTOR_PACK,
)
from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorRegistry,
)


DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY = WorkpageDescriptorRegistry(
    packs=(LOGISTICS_WORKPAGE_DESCRIPTOR_PACK,),
)
