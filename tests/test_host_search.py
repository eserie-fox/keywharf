from __future__ import annotations

import pytest

from keywharf.domain.errors import KeywharfError
from keywharf.domain.models import HostDefinition, HostEndpointOption
from keywharf.services.host_search import find_host_candidates


def host(name, aliases=(), addresses=()):
    return HostDefinition(
        server_name=name,
        aliases=list(aliases),
        endpoints=[HostEndpointOption(hostname=address) for address in addresses],
    )


@pytest.mark.parametrize(
    "query, expected",
    [
        ("quant", ["nc1-quant-01"]),
        ("NC1-QUANT-01", ["nc1-quant-01"]),
        (" TR ", ["nc1-quant-01"]),
        ("ANT.EXAMPLE", ["nc1-quant-01"]),
        ("missing", []),
    ],
)
def test_search_names_and_addresses_case_insensitively(query, expected):
    definitions = {"nc1-quant-01": host("nc1-quant-01", ["tr"], ["quant.example.test"])}
    assert find_host_candidates(definitions, query) == expected


def test_matching_tiers_prefer_exact_declared_identity_then_exact_address():
    definitions = {
        "quant": host("quant"),
        "alias-owner": host("alias-owner", ["work"]),
        "address-owner": host("address-owner", addresses=["quant", "work", "node"]),
        "quant-worker": host("quant-worker"),
        "prefix-owner": host("prefix-owner", addresses=["node.example.test"]),
        "nc1-quant-01": host("nc1-quant-01"),
    }
    assert find_host_candidates(definitions, "quant") == ["quant"]
    assert find_host_candidates(definitions, "work") == ["alias-owner"]
    assert find_host_candidates(definitions, "node") == ["address-owner"]


def test_prefix_matches_do_not_hide_other_substring_matches():
    definitions = {
        "quant-worker": host("quant-worker", addresses=["quant-worker.example.test"]),
        "nc1-quant-01": host("nc1-quant-01"),
        "address-owner": host("address-owner", addresses=["quant.example.test"]),
    }
    assert find_host_candidates(definitions, "quant") == [
        "address-owner",
        "nc1-quant-01",
        "quant-worker",
    ]


@pytest.mark.parametrize("reverse", [False, True])
def test_candidates_are_distinct_hosts_in_stable_order(reverse):
    entries = [
        ("node-B", host("node-B", ["node-backup"], ["shared.test", "shared.test"])),
        ("Node-a", host("Node-a", ["node-active"], ["shared.test"])),
    ]
    definitions = dict(reversed(entries) if reverse else entries)
    assert find_host_candidates(definitions, "node") == ["Node-a", "node-B"]
    assert find_host_candidates(definitions, "shared.test") == ["Node-a", "node-B"]


@pytest.mark.parametrize("query", ["", " \t\n"])
def test_empty_queries_are_rejected_even_for_empty_catalog(query):
    with pytest.raises(KeywharfError):
        find_host_candidates({}, query)
