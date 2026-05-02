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

- **`list_pending_devices` URL pattern wrong.** `/integration/v1/sites/{UUID}/devices/pending` returns 400 with `'pending' is not a valid 'deviceId' value` — the controller parses `pending` as a `{deviceId}` path parameter. The real endpoint probably uses a query parameter (e.g. `/devices?status=pending`) or a different path. Verified live 2026-05-01; check the integration spec for the correct shape.
- **Duplicate `list_radius_profiles` registration warning.** Cause now confirmed: there are two functions named `list_radius_profiles`, one in `src/tools/radius.py` (uses `/ea/sites/{site_id}/rest/radiusprofile`) and one in `src/tools/reference_data.py` (uses `/integration/v1/sites/{site_id}/radius/profiles`). Both get registered under the same MCP tool name; whichever loads second wins (currently `reference_data`). Startup logs `Component already exists: tool:list_radius_profiles@`. Decide which one stays and rename or remove the other.
- **WLAN passphrase exposure in `list_wlans`.** Response includes `x_passphrase` in plaintext. Design call: redact by default, opt-in via flag to include? Affects any caller that pipes WLAN data into a less-trusted context.
- **Cosmetic — `Settings.resolve_secrets_from_keychain` docstring.** References `__pydantic_private__`; the implementation actually uses `object.__setattr__(self, "_secret_sources", sources)`.
- **Cloud SM endpoint live exercise.** Surviving Site Manager tools (`list_all_sites_aggregated`, `list_hosts`, `get_host`, `get_isp_metrics`, `query_isp_metrics`) are unit-tested but not exercised against a real cloud SM controller — would need an SM-API key separate from the local API key.

## How to refresh this list

When you finish a session that turned up small follow-up items, append them here rather than letting them dissolve into commit messages. When an item turns into a real phase of work, promote it to `DEVELOPMENT_PLAN.md` and remove it here.
