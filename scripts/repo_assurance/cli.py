from __future__ import annotations

import argparse
from collections.abc import Callable

from scripts.repo_assurance.core import AssuranceState, Collector
from scripts.repo_assurance.release import run_release_domain
from scripts.repo_assurance.repo_metadata import run_metadata_domain
from scripts.repo_assurance.schema_governance import (
    run_governance_domain,
    run_schema_domain,
)
from scripts.repo_assurance.secrets import run_secrets_domain
from scripts.repo_assurance.traces import run_traces_domain

DOMAIN_ORDER = (
    "schema",
    "governance",
    "metadata",
    "release",
    "secrets",
    "traces",
)
FAST_ASSURANCE_DOMAINS = (
    "schema",
    "governance",
    "metadata",
    "release",
    "secrets",
)
DOMAIN_RUNNERS: dict[str, Callable[[AssuranceState], None]] = {
    "schema": run_schema_domain,
    "governance": run_governance_domain,
    "metadata": run_metadata_domain,
    "release": run_release_domain,
    "secrets": run_secrets_domain,
    "traces": run_traces_domain,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run repo assurance domains over schemas, governance, metadata, "
            "release packaging, secrets, and traces."
        )
    )
    parser.add_argument(
        "--domain",
        action="append",
        choices=DOMAIN_ORDER,
        help="Repeatable assurance domain selector.",
    )
    parser.add_argument("--traces-only", action="store_true")
    parser.add_argument("--schemas-only", action="store_true")
    parser.add_argument("--secrets-only", action="store_true")
    args = parser.parse_args(argv)

    legacy_flags = [args.traces_only, args.schemas_only, args.secrets_only]
    if sum(bool(flag) for flag in legacy_flags) > 1:
        parser.error("legacy validation mode flags are mutually exclusive")
    if args.domain and any(legacy_flags):
        parser.error("cannot combine legacy validation mode flags with --domain")

    domains = _resolve_domains(args)
    collector = Collector()
    state = AssuranceState(collector=collector)
    for domain in domains:
        DOMAIN_RUNNERS[domain](state)
    return collector.report()


def _resolve_domains(args: argparse.Namespace) -> list[str]:
    if args.schemas_only:
        return list(FAST_ASSURANCE_DOMAINS)
    if args.traces_only:
        return ["traces"]
    if args.secrets_only:
        return ["secrets"]
    if args.domain:
        selected: list[str] = []
        seen: set[str] = set()
        for domain in args.domain:
            if domain in seen:
                continue
            seen.add(domain)
            selected.append(domain)
        return selected
    return list(DOMAIN_ORDER)
