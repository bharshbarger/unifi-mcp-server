# UniFi MCP Server — TODO

## Source of truth

This file used to be a phase-by-phase roadmap. It went six months out of date (last refresh 2025-11-08, claiming v0.1.0 / 40 tools / 179 tests, while reality moved to v0.3.0 / ~194 tools / 1,230 tests). The historical content has been archived to `docs/archive/TODO-2025-11-archive.md` for reference.

The authoritative roadmap is now:

- **`DEVELOPMENT_PLAN.md`** — current implementation status, gap analysis, phased plan, version targets.
- **`CHANGELOG.md`** — what has shipped per release.
- **`API.md`** — current tool reference.

If a task isn't tracked in one of those, it lives below.

## Open follow-ups (small, not yet on the roadmap)

These came out of recent sessions and are too small to belong in `DEVELOPMENT_PLAN.md`. Pick them up opportunistically.

- **`list_firewall_policies` 500 passthrough.** When Zone-Based Firewall is not configured, the controller returns a 500 with an HTML body. Should be detected and surfaced as a typed `NotConfiguredError` like `list_firewall_zones` already does (which returns a 400 with `api.firewall.zone-based-firewall-not-configured`).
- **WLAN passphrase exposure in `list_wlans`.** Response includes `x_passphrase` in plaintext. Design call: redact by default, opt-in via flag to include? Affects any caller that pipes WLAN data into a less-trusted context.
- **Duplicate `list_radius_profiles` registration warning.** Startup logs `Component already exists: tool:list_radius_profiles@`. Likely a double `@server.tool` decorator in `src/tools/radius.py`.
- **Cosmetic — `Settings.resolve_secrets_from_keychain` docstring.** References `__pydantic_private__`; the implementation actually uses `object.__setattr__(self, "_secret_sources", sources)`.
- **Cloud SM endpoint live exercise.** Surviving Site Manager tools (`list_all_sites_aggregated`, `list_hosts`, `get_host`, `get_isp_metrics`, `query_isp_metrics`) are unit-tested but not exercised against a real cloud SM controller — would need an SM-API key separate from the local API key.
- **Broader live exercise of post-trim local tool surface.** `list_devices`, `list_devices_by_type`, `search_clients`, QoS reads, port profile reads, etc. against a real UCK-G2 to validate end-to-end after the keychain refactor and SM trim.

## How to refresh this list

When you finish a session that turned up small follow-up items, append them here rather than letting them dissolve into commit messages. When an item turns into a real phase of work, promote it to `DEVELOPMENT_PLAN.md` and remove it here.
