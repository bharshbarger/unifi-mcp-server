# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-05-01

This release covers 36 commits since `0.2.4` across firewall, traffic, switching, diagnostics, secrets handling, and Site Manager surface area. The major-bump is driven by the Site Manager tool/model trim — calls to the removed names will fail and require update.

### Breaking

- **Site Manager API trim** (`9bca756`). Removed 6 tools: `get_internet_health`, `get_site_health_summary`, `get_cross_site_statistics`, `list_vantage_points`, `compare_site_performance`, `get_version_control`. Removed 8 unused models (SiteHealthSummary, InternetHealthMetrics, CrossSiteStatistics, VantagePoint, SitePerformanceMetrics, CrossSitePerformanceComparison, ISPMetrics, VersionControl). Removed MCP resources `site-manager://health` and `site-manager://internet-health`. Survivors: `list_all_sites_aggregated`, `list_hosts`, `get_host`, `get_isp_metrics`, `query_isp_metrics`, plus a new `list_devices`. Net −1,306 lines; the SM client now centralizes HTTP through `_request`.

### Added

- **Switching API** (`c48384b`, `6003c60`). New tools for switch stacks, MC-LAG domains, and LAGs: `list_switch_stacks`, `get_switch_stack`, `list_mclag_domains`, `get_mclag_domain`, `list_lags`, `get_lag_details`. Models in `src/models/switching.py`. Fully TDD-built.
- **Diagnostics module** (`74531de`). Network References (`get_network_references`), Speed Test (`run_speed_test`, `get_speed_test_status`, `get_speed_test_history`), and Spectrum Scan (`get_spectrum_scan`, `list_spectrum_interference`).
- **Firewall groups CRUD** (`016c573`, `1c91509`). Address/port group create/read/update/delete with port matching on policies.
- **Zone-based firewall policies** (`af1cd56`, `a2d5139`). Policy CRUD against the v2 endpoint with a zone-name resolver.
- **Traffic Flows v2** (`44a6cda`, `73c3b0f`). Rewritten against the local v2 endpoint; new `find_flows_for_rule_reference` tool.
- **macOS Keychain secrets** (`3b2a977`). `Settings.resolve_secrets_from_keychain()` resolves `api_key` and `site_manager_api_key` in order: env var → Keychain (`security` CLI) → `ConfigurationError`. `Settings.describe_secret_sources()` exposes per-key provenance, logged at startup. `Settings.resolved_site_manager_api_key()` and `get_site_manager_headers()` let the SM client use a dedicated key when provided. `scripts/seed-keychain.sh` interactive seeder. README and `.env.example` updated; env vars are now a fallback for non-macOS / CI hosts.
- **Claude Code stdio launcher** (`4d2e16b`). `scripts/launch-mcp.sh` wraps the venv entry point so Claude Code can spawn the server over stdio with no secrets in harness config — secrets stay in Keychain.
- **WLAN updates** (`a8e0ea8`, `d92cc90`). `update_wlan` parameter parity, AP radio channel config, `wlan_bands` parameter.
- **`update_port_forward`** tool (`e6a943d`).

### Changed

- **Cross-cutting cleanup** (`449ea57`). `coerce_bool` adopted across 19 tool modules for uniform `dry_run` / `confirm` parsing. `datetime.now()` → `datetime.now(timezone.utc)` in audit and backup paths. Pydantic v1 → v2 validator migration in `src/webhooks/receiver.py`. Process-shared `CacheClient` pool keyed by `Settings` id. `_append_line` audit helper extracted. `uv.lock` pinned to `exclude-newer = 2026-04-19T17:52:51Z`.
- **API client** (`449ea57`). `authenticate()` is now idempotent. Rate-limiter token wait runs *outside* the bucket lock so concurrent waiters compute deadlines independently.
- **Documentation** (`647b6ba`, `bc80620`). `UNIFI_API.md` bumped to v10.3.55. `DEVELOPMENT_PLAN.md` rewritten for full-API-coverage roadmap (v10.3.55 + Site Manager v1.0 + Protect v6.2.83).
- **Security hardening + main.py refactor** (`2359fe1`).

### Fixed

- **`Network.vlan_id` blank-coercion** (`d82bf77`). The local controller returns `vlan: ""` for VLAN-disabled networks (the default LAN); the model declared `vlan_id: int | None` with no coercion hook so `list_vlans` crashed with a Pydantic `ValidationError` before returning data. A `mode='before'` field validator now maps blank/whitespace strings to `None` while letting numeric strings still parse. 6 model-layer tests + 1 tool-layer regression test.
- **`update_wan_dns`** (`449ea57`). Switched from partial PUT to GET-merge-PUT — the legacy V1 `networkconf` endpoint expects the full network object on PUT, so the previous partial PUT was clobbering unrelated fields on every call.
- **Local API mode response normalization** (`a003b68`, `b645533`, `a13032d`). Single-object response unwrap and parsing fixes across all tool modules.
- **Cloud-EA + Site Manager hardening** (`d021b7f`). API compatibility fixes.
- **Integration API compatibility** (`c0b61cc`). ACLs, zones, devices, traffic flows.
- **Firewall zones** (`5c98370`, #54). Zone PUT payload now uses `networkIds` (the API contract), not `networks`.
- **Network model** (`229e07e`). VLAN model alias + API field name; removed immutable `purpose` parameter.
- **WLAN** (`a0a9da4`). `update_wlan` syncs the legacy `wlan_band` field when `wlan_bands` is updated.
- **Local API bug pile** (`5c18c9e`, `79277ae`, #57). Cumulative bug fixes in local-mode tools and removal of endpoints that don't exist in the local API.
- **Dependabot vulnerabilities** (`e0d3b88`).

### Tests

- 1,230 unit tests passing (up from 1,159 at 0.2.4).
- New: `tests/unit/models/test_network.py`, `tests/unit/tools/test_networks_tools.py::TestListVlans::test_list_vlans_handles_blank_vlan_field`, `tests/unit/api/test_site_manager_client.py`, `tests/unit/config/test_keychain.py` (12 tests), full TDD suites for Switching and Diagnostics.

### Known issues / open follow-ups

- `list_firewall_policies` returns a controller 500 (HTML body) when Zone-Based Firewall is not configured; should be mapped to a typed `NotConfiguredError` like `list_firewall_zones` does.
- `list_wlans` returns `x_passphrase` in plaintext; redact-by-default with an opt-in flag is open for design.
- Startup log warns `Component already exists: tool:list_radius_profiles@`; pre-existing duplicate registration in `src/tools/radius.py`.

## [0.2.4] - 2026-02-19

### Fixed

- **Critical startup bug (issue #42)**: `ImportError: cannot import 'config' from 'agnost'` prevented the server from starting for all users, even when `AGNOST_ENABLED=false`. Root cause: `agnost` v0.1.13 removed the `config` export, and the old code imported it unconditionally at module top-level. Fixed by moving agnost imports inside the conditional block — they now only execute when `AGNOST_ENABLED=true` and `AGNOST_ORG_ID` is set, and any import or runtime failure is gracefully caught and logged as a warning.

### Tests

- Added `tests/unit/test_main_agnost_import.py` with 3 regression tests covering missing `config` export, agnost not installed, and agnost disabled scenarios.
- Test count: 1,159 passing (up from 1,156).

## [0.2.3] - 2026-02-18

### Added

**RADIUS & Guest Portal — Complete CRUD (4 new tools)**

- `get_radius_account` — Retrieve a single RADIUS account by ID; password field auto-redacted
- `update_radius_account` — Update username, password, VLAN, tunnel type, enabled status, and notes; confirm/dry-run support
- `get_hotspot_package` — Retrieve a single hotspot package by ID
- `update_hotspot_package` — Update name, duration, bandwidth limits, quotas, price, currency, and enabled status; confirm/dry-run support

These complete full CRUD for RADIUS accounts and hotspot packages. Phase 6 (Enhanced RADIUS & Guest Portal) is now feature-complete.

### Fixed

- **QoS Tools**: Fixed runtime `TypeError` in 6 `audit_action` calls in `qos.py` that incorrectly used `action=` keyword argument instead of the required `action_type=`. Affected `create_qos_profile`, `update_qos_profile`, `configure_smart_queue`, `disable_smart_queue`, `create_traffic_route`, `update_traffic_route`. Would have crashed at runtime whenever audit logging was enabled.
- **Site Manager**: Removed duplicate `@require_site_manager` decorator on `get_sdwan_config_status` (was applied twice — redundant and confusing).
- **Topology Tests**: Fixed 6 `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` warnings in the topology test suite. Root cause: 6 tests called `client.settings.get_integration_path()` through an auto-created `AsyncMock` (because `mock_instance.settings` was not set). Fixed by adding `mock_instance.settings = mock_settings` to each affected test.
- **Backup Client**: Added 3 missing methods to `UniFiClient` that `backups.py` calls at runtime:
  - `get_restore_status(operation_id)` — returns `not_supported` stub (endpoint not in UniFi API)
  - `configure_backup_schedule(...)` — `PUT /proxy/network/api/s/{site}/rest/backup/schedule`
  - `get_backup_schedule(site_id)` — `GET /proxy/network/api/s/{site}/rest/backup/schedule`
  Previously these silently fell back to an `AttributeError` handler in `backups.py`.

### Tests

- Added `TestUniFiClientBackupMethods` with 5 tests covering the new backup client methods.
- Test count: 1,156 passing (up from 1,128).
- Zero `RuntimeWarning` coroutine warnings (down from 6).

## [0.2.2] - 2026-02-16

### 🎉 Feature Release - Port Profile Management & Security Hardening

This release adds comprehensive switch port management capabilities, fixes critical security vulnerabilities, corrects API endpoint issues, and improves code quality across the codebase.

### Added

**Port Profile & Switch Port Management (8 new tools)**

- `list_port_profiles` - Paginated listing of switch port profiles with filtering
- `get_port_profile` - Fetch detailed port profile configuration by ID
- `create_port_profile` - Create port profiles with full configuration:
  - PoE settings (auto, passthrough, 24V, 48V, passthrough+)
  - VLAN configuration (native, trunk, excluded VLANs)
  - 802.1X port-based authentication
  - LLDP-MED voice VLAN support
  - Port speed/duplex configuration
  - Port isolation and storm control
- `update_port_profile` - Update profiles with fetch-then-merge to preserve fields
- `delete_port_profile` - Delete port profiles with existence verification
- `get_device_port_overrides` - Retrieve per-port overrides and full port table for devices
- `set_device_port_overrides` - Apply port-specific configuration:
  - Smart merge by `port_idx` (preserves other ports)
  - Full replace mode for complete reconfiguration
  - Validation of required fields (`port_idx`, `portconf_id`)
- `get_device_by_mac` - Look up devices by MAC address for port configuration

**Pydantic Models**

- `PortProfile` - Complete port profile data model with validation
- `PortOverride` - Per-port override configuration
- `PortTableEntry` - Read-only port status and statistics
- `DuplicateResourceError` - Exception for duplicate name detection

**Test Coverage**

- 75 new unit tests for port profile tools (100% of new code covered)
- Total test count: 1,068 (up from 990)
- All tests passing across Python 3.10, 3.11, 3.12

### Security

**Critical Dependency Updates (18 vulnerabilities fixed)**

- **FastMCP**: 0.1.0 → 2.14.5
  - Fixed CVE-2025-66416 (high severity)
  - Fixed auth integration confused deputy attack (high)
  - Fixed reflected XSS in callback page (medium)
  - Fixed Windows command injection (medium)
- **MCP SDK**: 1.16.0 → 1.26.0
  - Enabled DNS rebinding protection by default (high)
- **cryptography**: 43.0.0 → 46.0.5
  - Fixed SECT curve subgroup attack vulnerability (high)
- **httpx**: 0.27.0 → 0.28.1
- **pydantic**: 2.0.0 → 2.12.5
- **agnost**: 0.1.8 → 0.1.12
- **urllib3**: Added >=2.3.0 requirement
  - Fixed decompression bomb safeguards bypass (high)
  - Fixed unbounded links in decompression chain (high)
  - Fixed O(n²) streaming API DoS (high)

**Security Hardening**

- Removed `session-work.md` and `TEST_RESULTS.md` from git tracking (contained real internal IPs)
- Added both files to `.gitignore` to prevent future leaks
- Replaced PII in `SECURITY.md` (placeholder emails → GitHub Security Advisories)
- MAC address sanitization in logs and error messages (masked to `aa:bb:cc:xx:xx:xx`)
- Git history verified clean - no secrets ever committed

### Fixed

**API Endpoint & Payload Corrections**

- **RADIUS Tools** - Corrected endpoints and field names:
  - Profile endpoints: `/integration/v1/.../radius/profiles` → `/ea/sites/.../rest/radiusprofile`
  - Account endpoints: `/integration/v1/.../radius/accounts` → `/ea/sites/.../rest/account`
  - Password field: `password` → `x_password` (actual UniFi API field)
  - VLAN field: `vlan_id` → `vlan`
  - Auto-populate `tunnel_type`/`tunnel_medium_type` when VLAN specified
  - Secrets redacted (`***REDACTED***`) in all responses
  - Fixed list response handling at 5 locations (prevents `AttributeError` on `.get()`)

- **Firewall Tools** - New payload fields for proper rule creation:
  - Added `ruleset` (default `WAN_IN`) and `rule_index` (default `2000`)
  - Added `src_networkconf_id`/`dst_networkconf_id` with type variants (default `None`, typed `str | None`)
  - Added connection state flags: `state_established`, `state_related`, `state_new`, `state_invalid`
  - Added traffic `logging` flag
  - Fixed parameter names: `source`/`destination` → `src_address`/`dst_address`

- **WLAN Tools** - New creation parameters:
  - Added `networkconf_id` - associate SSID with specific network
  - Added `ap_group_ids`/`ap_group_mode` - per-AP-group broadcasting
  - Added `wlan_bands` - band selection (`2g`, `5g`, or both)
  - Added IoT optimization and minimum data rate controls

- **Network Config Tools** - Fixed VLAN field name (`vlan_id` → `vlan`)

- **All Tools** - Boolean parameter coercion (`"true"` → `True`) for MCP JSON-RPC compatibility

**Bug Fixes**

- Fixed `dry_run` requiring `confirm=True` - `validate_confirmation()` now accepts `dry_run` parameter
- Fixed missing `DuplicateResourceError` exception (was imported but not defined)
- Fixed RADIUS response crashes where list responses were passed to `.get()` or Pydantic constructors
- Updated all 55 call sites across 16 tool modules for dry_run fix

**Code Quality**

- Added full type hints to `coerce_bool(value: bool | str | None) -> bool`
- Added full type hints to `validate_confirmation(confirm: bool | str | None, operation: str, dry_run: bool | str = False) -> None`
- Port profile tools validate responses through Pydantic models before returning
- Fixed import ordering (isort) across all files

### Changed

- Tool count: 74 → 82+ MCP tools
- Test count: 990 → 1,068 tests
- Updated version references in README.md, CLAUDE.md, pyproject.toml

### Technical Details

**Commits**

- `94277cb` - Fix RADIUS, firewall, WLAN, network endpoints/payloads (29 files)
- `20efe10` - Add port profile and device port override tools (6 files)
- `b7c0489` - Remove PII, harden repo for public release (4 files)
- `448b916` - Add missing DuplicateResourceError exception (2 files)
- `653d957` - Allow dry_run without confirm, fix firewall param names
- `360339f` - Add type hints to coerce_bool and validate_confirmation
- `d666965` - Validate port profile responses through Pydantic models
- `e77129c` - Fix MAC leak in logs/errors, firewall defaults, RADIUS response handling
- `ffe8d86` - Merge PR #35: port profile tools, API fixes, and security hardening
- `9feb15b` - Style: apply black and isort formatting fixes
- `ddaa9e9` - Fix(deps): update dependencies to address security vulnerabilities
- `5674286` - Style: fix isort import ordering
- `ffc1e6e` - Docs: update documentation for v0.2.2 release

**Statistics**

- 40 files changed (+2,726 / -1,235 lines)
- 8 new MCP tools (total: ~82)
- 75 new unit tests (total: 1,068)
- 3 new Pydantic models
- 1 new exception class
- 18 security vulnerabilities fixed
- 0 test failures
- 6 warnings (pre-existing async mock coroutines)

## [0.2.1] - 2026-01-25

### 🔧 Critical Bug Fix - Topology Tools

Fixed topology tools that were completely non-functional due to using non-existent API endpoints.

### Fixed

- **Topology Tools (5 tools)**: Rewrote all topology tools to use correct Integration API endpoints
  - Changed from non-existent `/api/s/{site}/stat/topology` to proper Integration API endpoints
  - Now uses `/v1/sites/{siteId}/devices` and `/v1/sites/{siteId}/clients`
  - Updated data model field names to match Integration API response format
  - Fixed endpoint path construction using `get_integration_path()` for proper API translation
  - Added pagination support for large device/client lists
  - Fixed network depth calculation and client connection type detection

### Added

- **Integration Test Framework**: Comprehensive test harness for real-world validation
  - Multi-environment support (6 environments: 2 local + 4 cloud)
  - API mode testing (local, cloud-v1, cloud-ea)
  - Intelligent test skipping for unsupported API features
  - Detailed reporting with pass/fail/skip statistics
  - JSON export for CI/CD integration
  - Dry-run mode for test planning
  - Test suite organization with setup/teardown hooks
- **Topology Test Suite**: 8 comprehensive tests with 100% pass rate on local APIs
- **Test Documentation**: Complete guide for writing and running integration tests

### Technical Details

**Data Model Changes**:

- `device._id` → `device.id`
- `device.mac` → `device.macAddress`
- `device.ip` → `device.ipAddress`
- `uplink.device_id` → `uplink.deviceId`
- `device.state` (int) → `device.state` (string: "CONNECTED"|other)

**Test Results**:

- 16/16 tests PASSED on local APIs (100%)
- 32/32 tests SKIPPED on cloud APIs (expected - topology not supported)
- 0 FAILED
- Total test duration: 6.97s across 6 environments

**API Limitations Documented**:

- Local APIs: Full topology support
- Cloud APIs (v1 & EA): Aggregate statistics only, no device-level data

## [0.2.0] - 2026-01-25

### 🎉 Production Release - All Features Complete

This is the definitive v0.2.0 release with all 7 planned feature phases complete, comprehensive testing, and production-ready quality.

### Added

**Phase 1: QoS Enhancements (11 tools)**

- QoS profile management (list, get, create, update, delete)
- Reference QoS profiles and ProAV templates
- Traffic routing with time-based schedules
- Application-based QoS configuration
- Coverage: 82.43% (46 tests passing)

**Phase 2: Backup & Restore (8 tools)**

- Manual and automated backup creation
- Backup listing and download with checksum verification
- Backup restore functionality
- Automated scheduling with cron expressions
- Cloud synchronization tracking
- Coverage: 86.32% (10 tests passing)

**Phase 3: Multi-Site Aggregation (4 tools)**

- Cross-site device and client analytics
- Site health monitoring and scoring
- Side-by-side site comparison
- Consolidated reporting across locations
- Coverage: 92.95% (10 tests passing)

**Phase 4: ACL & Traffic Filtering (7 tools)**

- Layer 3/4 access control list management
- Traffic matching lists (IP, MAC, domain, port groups)
- Firewall policy automation
- Rule ordering and priority management
- Coverage: 89.30-93.84%

**Phase 5: Site Management (9 tools)**

- Multi-site provisioning and configuration
- Site-to-site VPN setup
- Device migration between sites
- Advanced site settings management
- Configuration export for backup
- Coverage: 92.95% (10 tests passing)

**Phase 6: RADIUS & Guest Portal (6 tools)**

- RADIUS profile configuration (802.1X authentication)
- RADIUS accounting server support
- Guest portal customization
- Hotspot billing and voucher management
- Session timeout and redirect control
- Coverage: 69.77% (17 tests passing)

**Phase 7: Network Topology (5 tools)**

- Complete network topology graph retrieval
- Multi-format export (JSON, GraphML, DOT)
- Device interconnection mapping
- Port-level connection tracking
- Network depth analysis
- Coverage: 95.83% (29 tests passing)

### Quality Metrics

- **74 Total MCP Tools**: Comprehensive UniFi network management
- **990 Tests Passing**: Robust validation across all modules
- **78.18% Test Coverage**: 4,865 of 6,105 statements covered
- **18/18 CI/CD Checks Passing**: All quality gates met
- **Zero Security Vulnerabilities**: Clean security scans
- **30+ AI Assistant Example Prompts**: Comprehensive usage documentation

### Documentation

- Added comprehensive VERIFICATION_REPORT.md documenting complete testing and validation
- Added 30+ AI assistant example prompts across 10 categories in API.md
- Updated API.md with all 74 tools documented with examples
- Updated UNIFI_API.md with complete API endpoint reference

### Fixed

- CodeQL security alerts resolved (wrong parameter names in QoS tools)
- Secret redaction in RADIUS dry-run logging
- Pre-commit hook failures (import formatting)
- Duplicate function definitions
- Test coverage gaps in critical paths

### Changed

- License: Apache 2.0
- Architecture: All 7 feature phases complete
- Test coverage improved from 41.27% to 78.18%
- Total tests increased from 228 to 990

### Release Artifacts

- Docker: ghcr.io/enuno/unifi-mcp-server:0.2.0 (multi-arch: amd64, arm64, arm/v7)
- npm: unifi-mcp-server@0.2.0
- PyPI: unifi-mcp-server==0.2.0
- GitHub: <https://github.com/enuno/unifi-mcp-server/releases/tag/v0.2.0>

See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for complete details.

---

## [0.1.4] - 2025-11-17

### Version Correction Notice

This release corrects a premature v0.2.0 release. The code is identical to v0.2.0, but v0.1.4 is the correct version number. The true v0.2.0 release is planned for Q1 2025 with complete Zone-Based Firewall implementation, full Traffic Flow monitoring, and 80%+ test coverage.

### Added

- Comprehensive WiFi tools test suite with 23 tests and 70.34% coverage
- Cloud API compatibility for Site model using Pydantic v2 validation_alias
- Support for both Cloud API (`siteId`, `isOwner`) and Local API (`_id`, `name`) schemas
- 17 comprehensive unit tests for Site model covering Cloud/Local API compatibility
- Automatic name fallback generation for Cloud API sites without explicit names

### Fixed

- **GitHub Issue #3**: Cloud API schema mismatch in Site model
  - Fixed Pydantic validation errors when using Cloud API
  - Site model now accepts `siteId` (Cloud) and `_id` (Local) field names
  - Site model now accepts `siteName` and `name` field variations
  - Added model_validator to generate fallback names from site IDs
- All 16 failing WiFi tests resolved (23/23 now passing)
  - Fixed mock return value structures to match UniFi API response format
  - Added missing `security` parameter to WLAN creation tests
  - Changed exception types from ConfirmationRequiredError to ValidationError
  - Fixed missing API call mocks for update/delete operations
  - Fixed field name assertions (passphrase → x_passphrase)
  - Rewrote statistics tests to handle dual API calls correctly
- Python 3.10 compatibility issues resolved
- Import sorting issues fixed per isort/pre-commit requirements
- Ruff linting errors in WiFi test suite resolved
- Missing ValidationError import added to Site model tests
- Traffic flows formatting with Black

### Changed

- Site model made backward compatible with existing Local API code
- Enhanced Site model with Cloud API-specific fields (`is_owner`)
- Improved test coverage from 36.83% to 41.27% overall
- Site model test coverage: 100%

### Technical Details

- All 228 tests passing
- Test coverage: 41.27%
- CI/CD pipelines: All checks passing
- Compatible with Python 3.10, 3.11, 3.12

## [0.2.0] - 2025-11-16 [PREMATURE - DO NOT USE]

### ⚠️ Version Correction Notice

**This version was published prematurely. Please use v0.1.4 instead, which contains identical code.**

The true v0.2.0 release is planned for Q1 2025 and will include:

- Complete Zone-Based Firewall (ZBF) implementation (~60% complete as of this release)
- Full Traffic Flow monitoring (~100% complete as of this release)
- Advanced QoS and traffic management
- Backup and restore operations
- 80%+ test coverage (currently 34%)

See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for the complete roadmap.

### Original v0.2.0 Release Notes (For Reference)

### Added

- Comprehensive WiFi tools test suite with 23 tests and 70.34% coverage
- Cloud API compatibility for Site model using Pydantic v2 validation_alias
- Support for both Cloud API (`siteId`, `isOwner`) and Local API (`_id`, `name`) schemas
- 17 comprehensive unit tests for Site model covering Cloud/Local API compatibility
- Automatic name fallback generation for Cloud API sites without explicit names

### Fixed

- **GitHub Issue #3**: Cloud API schema mismatch in Site model
  - Fixed Pydantic validation errors when using Cloud API
  - Site model now accepts `siteId` (Cloud) and `_id` (Local) field names
  - Site model now accepts `siteName` and `name` field variations
  - Added model_validator to generate fallback names from site IDs
- All 16 failing WiFi tests resolved (23/23 now passing)
  - Fixed mock return value structures to match UniFi API response format
  - Added missing `security` parameter to WLAN creation tests
  - Changed exception types from ConfirmationRequiredError to ValidationError
  - Fixed missing API call mocks for update/delete operations
  - Fixed field name assertions (passphrase → x_passphrase)
  - Rewrote statistics tests to handle dual API calls correctly
- Python 3.10 compatibility issues resolved
- Import sorting issues fixed per isort/pre-commit requirements
- Ruff linting errors in WiFi test suite resolved
- Missing ValidationError import added to Site model tests
- Traffic flows formatting with Black

### Changed

- Site model made backward compatible with existing Local API code
- Enhanced Site model with Cloud API-specific fields (`is_owner`)
- Improved test coverage from 36.83% to 41.27% overall
- Site model test coverage: 100%

### Technical Details

- All 228 tests passing
- Test coverage: 41.27%
- CI/CD pipelines: All checks passing
- Compatible with Python 3.10, 3.11, 3.12

## [0.1.3] - 2025-01-XX

### Initial Release

- Model Context Protocol (MCP) server for UniFi Network API
- Support for Cloud and Local Controller APIs
- Device, Client, Network, and Site management tools
- Traffic flow monitoring and analysis
- Zone-based firewall (ZBF) management
- WiFi network configuration
- Comprehensive test suite

[0.2.0]: https://github.com/enuno/unifi-mcp-server/compare/v0.1.3...v0.2.0
[0.1.4]: https://github.com/enuno/unifi-mcp-server/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/enuno/unifi-mcp-server/releases/tag/v0.1.3
