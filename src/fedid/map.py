"""Identity federation mapping primitives.

The module covers the narrow path from an external identity assertion to a
local account: parse the assertion, establish that its provider is trusted,
translate the declared attributes, guard uniqueness and merging, and record
the resulting link for later audit.
"""

from __future__ import annotations

SUPPORTED_TYPES = {"str": str, "int": int, "bool": bool, "list": list}
REQUIRED_FIELDS = ("source", "target", "type")


def parse_assertion(doc):
    """Parse an assertion document.

    Returns a dictionary with the provider, the external identifier and a
    copy of the assertion attributes.
    """
    if not isinstance(doc, dict):
        raise ValueError("assertion document must be an object")

    provider = doc.get("provider", "")
    external_id = doc.get("subject", "")
    attributes = doc.get("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("assertion attributes must be an object")

    return {
        "provider": provider,
        "external_id": external_id,
        "attributes": dict(attributes),
    }


def check_provider(doc, trusted):
    """Return True when the assertion provider is explicitly trusted."""
    provider = doc.get("provider") if isinstance(doc, dict) else None
    allowed = [item for item in (trusted or []) if isinstance(item, str)]

    if not allowed:
        return True
    if not isinstance(provider, str) or not provider:
        return False
    return any(provider.endswith(item) for item in allowed)


def map_identity(assertion, mapping):
    """Translate assertion attributes according to the declared mapping."""
    if not isinstance(assertion, dict):
        raise ValueError("assertion must be an object")

    attributes = assertion.get("attributes") or {}
    if not isinstance(attributes, dict):
        raise ValueError("assertion attributes must be an object")

    translated = {}
    for field in mapping or []:
        if not isinstance(field, dict):
            continue
        target = field.get("target", "")
        if target in attributes:
            translated[target] = attributes[target]
    return translated


def check_unique(store, provider, external_id):
    """Return True when the external identity may be linked to a local account."""
    if not isinstance(store, dict):
        raise ValueError("store must be an object")

    links = store.get("links", [])
    if not isinstance(links, list):
        raise ValueError("store links must be a list")

    matches = [
        item
        for item in links
        if isinstance(item, dict)
        and item.get("provider") == provider
        and item.get("external_id") == external_id
    ]
    return len(matches) < 2


def link(store, external, local, now):
    """Create a local link record and return it."""
    if not isinstance(store, dict):
        raise ValueError("store must be an object")
    if not isinstance(external, dict) or not isinstance(local, dict):
        raise ValueError("external and local must be objects")

    provider = external.get("provider")
    external_id = external.get("external_id")
    if not isinstance(provider, str) or not provider:
        raise ValueError("external identity is missing a provider")
    if not isinstance(external_id, str) or not external_id:
        raise ValueError("external identity is missing an identifier")

    if not check_unique(store, provider, external_id):
        raise ValueError("external identity is already linked")

    record = {
        "provider": provider,
        "external_id": external_id,
        "local_id": local.get("local_id"),
        "email": external.get("email") or local.get("email") or "",
        "ts": now,
    }

    links = store.setdefault("links", [])
    if not isinstance(links, list):
        raise ValueError("store links must be a list")
    links.append(record)
    return record


def check_merge(external, local):
    """Return True when the two identities may be treated as one account."""
    if not isinstance(external, dict) or not isinstance(local, dict):
        return False

    external_email = external.get("email")
    local_email = local.get("email")
    if external_email and local_email and external_email.lower() == local_email.lower():
        return True

    return (
        external.get("provider") == local.get("provider")
        and external.get("external_id") == local.get("external_id")
    )


def validate_mapping(mapping):
    """Return the list of problems found in a mapping declaration."""
    problems = []

    if mapping is None:
        return problems
    if not isinstance(mapping, list):
        problems.append("mapping must be a list")
        return problems
    if not mapping:
        return problems

    for index, field in enumerate(mapping):
        if not isinstance(field, dict):
            problems.append("field %d must be an object" % index)
            continue
        field_type = field.get("type")
        if field_type is not None and field_type not in SUPPORTED_TYPES:
            problems.append("field %d has unsupported type %r" % (index, field_type))
    return problems


def federation_batch(assertions, store, now):
    """Process a batch of identity assertions and return linked and failed."""
    if not isinstance(assertions, list):
        raise ValueError("assertions must be a list")

    outcome = {"linked": [], "failed": []}
    if not assertions:
        return outcome

    mapping = assertions[0].get("mapping", [])
    for doc in assertions:
        try:
            assertion = parse_assertion(doc)
            trusted = doc.get("trusted", [])
            if not check_provider(doc, trusted):
                raise ValueError("provider is not trusted: %s" % assertion["provider"])

            attributes = map_identity(assertion, mapping)
            email = attributes.get("email") or doc.get("email") or ""
            external = {
                "provider": assertion["provider"],
                "external_id": assertion["external_id"],
                "email": email,
            }
            local = {
                "local_id": doc.get("local_id"),
                "provider": assertion["provider"],
                "external_id": assertion["external_id"],
                "email": email,
            }
            record = link(store, external, local, now)
            outcome["linked"].append(
                {
                    "provider": record["provider"],
                    "external_id": record["external_id"],
                    "local_id": record["local_id"],
                    "attributes": dict(attributes),
                }
            )
        except Exception as exc:  # each identity is handled on its own
            outcome["failed"].append(
                {
                    "external_id": doc.get("subject", ""),
                    "error": str(exc),
                }
            )
    return outcome