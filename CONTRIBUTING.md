# Contributing

This registry is security-sensitive. A registry PR can affect what ChironAI users
are invited to install.

## Entry Requirements

- Use a stable extension `id` that matches the extension manifest id.
- Point `repository` to the canonical GitHub repository.
- Do not add version lists or mutable default refs to the registry.
- Declare compatibility and user-facing capabilities.
- Use only approved visibility values: `official`, `trusted`, `community`,
  `experimental`, or `blocked`.

## Review Requirements

- New publishers require manual review.
- Ownership, repository identity, publisher identity, or high-risk capability
  changes require manual review.
- Capability expansion requires explicit user consent in ChironAI before update
  activation.
- Compromised extensions, repositories, publishers, refs, or versions must be
  added to the blocklist before normal metadata changes.

