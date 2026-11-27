"""Identity federation mapping helpers."""

from .map import (
    check_merge,
    check_provider,
    check_unique,
    federation_batch,
    link,
    map_identity,
    parse_assertion,
    validate_mapping,
)

__all__ = [
    "parse_assertion",
    "check_provider",
    "map_identity",
    "check_unique",
    "link",
    "check_merge",
    "validate_mapping",
    "federation_batch",
]