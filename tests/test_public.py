import pytest

from fedid import (
    check_provider,
    check_unique,
    federation_batch,
    map_identity,
    parse_assertion,
)


def test_parse_assertion_extracts_provider_and_attributes():
    doc = {
        "provider": "idp-a",
        "subject": "u-1",
        "attributes": {"mail": "alice@example.com"},
    }

    parsed = parse_assertion(doc)

    assert parsed["provider"] == "idp-a"
    assert parsed["external_id"] == "u-1"
    assert parsed["attributes"] == {"mail": "alice@example.com"}
    with pytest.raises(ValueError):
        parse_assertion({"provider": "idp-a", "attributes": {}})


def test_check_provider_rejects_lookalike_provider():
    assert check_provider({"provider": "idp-a"}, ["idp-a"]) is True
    assert check_provider({"provider": "idp-a-evil"}, ["idp-a"]) is False
    assert check_provider({"provider": "evil-idp-a"}, ["idp-a"]) is False


def test_map_identity_uses_declared_source():
    assertion = {
        "provider": "idp-a",
        "external_id": "u-1",
        "attributes": {
            "mail": "alice@example.com",
            "email": "decoy@example.com",
        },
    }
    mapping = [{"source": "mail", "target": "email", "type": "str"}]

    assert map_identity(assertion, mapping) == {"email": "alice@example.com"}


def test_check_unique_blocks_second_local_account():
    store = {"links": [], "audit": []}

    assert check_unique(store, "idp-a", "u-1") is True

    store["links"].append(
        {"provider": "idp-a", "external_id": "u-1", "local_id": "local-1"}
    )

    assert check_unique(store, "idp-a", "u-1") is False


def test_federation_batch_keeps_identities_independent():
    assertions = [
        {
            "provider": "idp-a",
            "subject": "u-1",
            "attributes": {"mail": "alice@example.com"},
            "mapping": [{"source": "mail", "target": "email", "type": "str"}],
            "trusted": ["idp-a"],
            "local_id": "local-1",
        },
        {
            "provider": "idp-b",
            "subject": "u-2",
            "attributes": {"correo": "bob@example.com"},
            "mapping": [{"source": "correo", "target": "email", "type": "str"}],
            "trusted": ["idp-b"],
            "local_id": "local-2",
        },
    ]
    store = {"links": [], "audit": []}

    result = federation_batch(assertions, store, "2026-11-19T00:00:00Z")

    assert len(result["linked"]) == 2
    assert result["failed"] == []
    assert result["linked"][0]["attributes"].get("email") == "alice@example.com"
    assert result["linked"][1]["attributes"].get("email") == "bob@example.com"
    assert result["linked"][0]["local_id"] == "local-1"
    assert result["linked"][1]["local_id"] == "local-2"