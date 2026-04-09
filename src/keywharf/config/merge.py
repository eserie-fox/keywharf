"""Deterministic deep-merge helpers for formal config."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def config_deep_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge mappings recursively; non-mapping values replace fully."""

    merged: dict[str, Any] = {key: deepcopy(value) for key, value in base.items()}

    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, Mapping) and isinstance(value, Mapping):
            merged[key] = config_deep_merge(base_value, value)
        else:
            merged[key] = deepcopy(value)

    return merged

