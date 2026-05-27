from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "extensions.json"
ALLOWED_OWNERS = {"Rayllienstery"}
ALLOWED_VISIBILITY = {"official", "trusted", "community", "experimental", "blocked"}
ALLOWED_TRUST = {"official", "trusted", "community", "experimental", "blocked", "unknown"}
ALLOWED_RISK = {"low", "medium", "high", "critical"}
FORBIDDEN_EXTENSION_KEYS = {"latest_version", "default_ref", "archive_url", "source_path"}
EXTENSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
CAPABILITY_ID_RE = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _require_string(errors: list[str], item: dict[str, object], key: str, *, ctx: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        _error(errors, f"{ctx}: {key} must be a non-empty string")
        return ""
    return value.strip()


def _github_owner(repository: str) -> str:
    parsed = urlparse(repository)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        return ""
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        return ""
    return parts[0]


def validate_registry(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["registry root must be an object"]
    if payload.get("schema_version") != "1":
        _error(errors, "schema_version must be '1'")
    if payload.get("registry") != "ChironAI Extensions Registry":
        _error(errors, "registry must be 'ChironAI Extensions Registry'")
    extensions = payload.get("extensions")
    if not isinstance(extensions, list) or not extensions:
        return errors + ["extensions must be a non-empty list"]

    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    seen_repos: set[str] = set()
    for index, raw in enumerate(extensions):
        ctx = f"extensions[{index}]"
        if not isinstance(raw, dict):
            _error(errors, f"{ctx}: entry must be an object")
            continue
        forbidden = sorted(FORBIDDEN_EXTENSION_KEYS.intersection(raw))
        if forbidden:
            _error(errors, f"{ctx}: registry must not store {', '.join(forbidden)}")
        ext_id = _require_string(errors, raw, "id", ctx=ctx)
        if ext_id and not EXTENSION_ID_RE.match(ext_id):
            _error(errors, f"{ctx}: id has invalid format")
        title = _require_string(errors, raw, "title", ctx=ctx)
        _require_string(errors, raw, "description", ctx=ctx)
        repository = _require_string(errors, raw, "repository", ctx=ctx)
        owner = _github_owner(repository)
        if not owner:
            _error(errors, f"{ctx}: repository must be https://github.com/owner/name")
        elif owner not in ALLOWED_OWNERS:
            _error(errors, f"{ctx}: repository owner '{owner}' is not approved")
        visibility = _require_string(errors, raw, "visibility", ctx=ctx)
        if visibility and visibility not in ALLOWED_VISIBILITY:
            _error(errors, f"{ctx}: visibility '{visibility}' is not allowed")
        if ext_id in seen_ids:
            _error(errors, f"{ctx}: duplicate id '{ext_id}'")
        if title.lower() in seen_titles:
            _error(errors, f"{ctx}: duplicate title '{title}'")
        if repository.lower() in seen_repos:
            _error(errors, f"{ctx}: duplicate repository '{repository}'")
        seen_ids.add(ext_id)
        seen_titles.add(title.lower())
        seen_repos.add(repository.lower())
        _validate_publisher(errors, raw.get("publisher"), ctx=ctx)
        _validate_compatibility(errors, raw.get("compatibility"), ctx=ctx)
        _validate_capabilities(errors, raw.get("capabilities"), ctx=ctx)
    _validate_blocklist(errors, payload.get("blocklist", []))
    return errors


def _validate_publisher(errors: list[str], raw: object, *, ctx: str) -> None:
    if not isinstance(raw, dict):
        _error(errors, f"{ctx}: publisher must be an object")
        return
    _require_string(errors, raw, "name", ctx=f"{ctx}.publisher")
    url = _require_string(errors, raw, "url", ctx=f"{ctx}.publisher")
    if url and not url.startswith("https://github.com/"):
        _error(errors, f"{ctx}.publisher: url must point to github.com")
    trust = _require_string(errors, raw, "trust_state", ctx=f"{ctx}.publisher")
    if trust and trust not in ALLOWED_TRUST:
        _error(errors, f"{ctx}.publisher: trust_state '{trust}' is not allowed")
    if not isinstance(raw.get("verified"), bool):
        _error(errors, f"{ctx}.publisher: verified must be boolean")


def _validate_compatibility(errors: list[str], raw: object, *, ctx: str) -> None:
    if not isinstance(raw, dict):
        _error(errors, f"{ctx}: compatibility must be an object")
        return
    if raw.get("app") != "chironai":
        _error(errors, f"{ctx}.compatibility: app must be chironai")
    if raw.get("extension_api_version") != "1":
        _error(errors, f"{ctx}.compatibility: extension_api_version must be 1")


def _validate_capabilities(errors: list[str], raw: object, *, ctx: str) -> None:
    if not isinstance(raw, list) or not raw:
        _error(errors, f"{ctx}: capabilities must be a non-empty list")
        return
    seen: set[str] = set()
    for index, item in enumerate(raw):
        cap_ctx = f"{ctx}.capabilities[{index}]"
        if not isinstance(item, dict):
            _error(errors, f"{cap_ctx}: capability must be an object")
            continue
        cap_id = _require_string(errors, item, "id", ctx=cap_ctx)
        if cap_id and not CAPABILITY_ID_RE.match(cap_id):
            _error(errors, f"{cap_ctx}: id has invalid format")
        if cap_id in seen:
            _error(errors, f"{cap_ctx}: duplicate capability id '{cap_id}'")
        seen.add(cap_id)
        _require_string(errors, item, "label", ctx=cap_ctx)
        _require_string(errors, item, "description", ctx=cap_ctx)
        risk = _require_string(errors, item, "risk", ctx=cap_ctx)
        if risk and risk not in ALLOWED_RISK:
            _error(errors, f"{cap_ctx}: risk '{risk}' is not allowed")
        if not isinstance(item.get("requires_user_consent"), bool):
            _error(errors, f"{cap_ctx}: requires_user_consent must be boolean")


def _validate_blocklist(errors: list[str], raw: object) -> None:
    if not isinstance(raw, list):
        _error(errors, "blocklist must be a list")
        return
    for index, item in enumerate(raw):
        ctx = f"blocklist[{index}]"
        if not isinstance(item, dict):
            _error(errors, f"{ctx}: entry must be an object")
            continue
        match = item.get("match")
        if not isinstance(match, dict) or not match:
            _error(errors, f"{ctx}: match must be a non-empty object")
        _require_string(errors, item, "reason", ctx=ctx)
        _require_string(errors, item, "created_at", ctx=ctx)


def main() -> int:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    errors = validate_registry(payload)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print(f"OK: {REGISTRY_PATH.name} contains {len(payload['extensions'])} extension entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

