# ChironAI Extensions Registry

Canonical registry for ChironAI extensions.

This repository intentionally stores extension discovery metadata only. Version
lists, README content, release archives, tags, and explicit refs are resolved
from each extension repository at runtime by ChironAI.

## Registry Contract

- `extensions.json` is the public registry entry point.
- Every entry must point to a GitHub repository owned by an approved publisher.
- Registry entries must not store `latest_version`, `default_ref`, `archive_url`,
  or branch defaults.
- ChironAI resolves the latest release, available versions, README, archive URL,
  commit SHA, and provenance from the extension repository.
- Every install/update must pass ChironAI manifest validation and security scan
  before activation.

## Validation

Run:

```bash
python scripts/validate_registry.py
```

The same validator runs in GitHub Actions on every pull request and push.

