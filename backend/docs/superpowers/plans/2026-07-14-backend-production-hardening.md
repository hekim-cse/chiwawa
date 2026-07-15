# Backend Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` for every behavior change and
> `superpowers:verification-before-completion` before reporting completion.
> Execute inline in this workspace; do not stage or commit without explicit user
> authorization.

**Goal:** Make the backend safe for a single-host, multi-worker production deployment
using shared local SQLite and private local photo storage.

**Architecture:** Development keeps an in-memory `AppState`; production uses a
function-scoped SQLite snapshot transaction and a separate SQLite OAuth-state store.
Pure ASGI middleware protects the request boundary, while focused adapters own local
photo files and upload admission.

**Tech Stack:** Python 3.13+, FastAPI 0.139+, Pydantic v2, SQLite WAL, Pillow,
PyJWT, pytest, Ruff, basedpyright, uv.

## Global Constraints

- Modify `backend/` only; never edit `frontend/` or `ai/`.
- Do not add S3 or another object store.
- Production support is one host with multiple workers sharing one local DB and photo root.
- Preserve the existing development-mode API flow.
- Preserve the pre-existing staged `../.idea/*` files.
- Add a failing regression test before every production behavior change.
- Do not stage, commit, push, or open a PR.

---

## File map

- `config.py`: typed deployment, storage, body, quota, rate, and readiness settings.
- `services/database.py`: secure SQLite connection and versioned migration runner.
- `services/state_store.py`: `StateSnapshot` and SQLite request transaction.
- `services/oauth_state_store.py`: short-lived atomic OAuth issue/consume operations.
- `state.py`: in-request aggregate and ownership data only.
- `dependencies.py`: centralized state, actor, OAuth store, and trip-access dependencies.
- `middleware/request_security.py`: early upload auth, request-size limits, request ID,
  and baseline security headers.
- `services/local_photo_store.py`: confined `0700` directories, `0600` files, trash delete.
- `services/upload_admission.py`: SQLite rate/concurrency leases and quota checks.
- `services/memorial_photos.py`: photo application orchestration and normalized metadata.
- `schemas/*`, `services/schedule.py`, `services/wanted_places.py`: PATCH and reference rules.
- `routers/*`, `main.py`, `routers/health.py`: production auth, lifecycle, errors, readiness,
  and OpenAPI declarations.

---

### Task 1: Typed production configuration and versioned SQLite migrations

**Files:**
- Modify: `src/chiwawa_backend/config.py`
- Modify: `src/chiwawa_backend/services/database.py`
- Create: `src/chiwawa_backend/sql/003_app_state.sql`
- Create: `src/chiwawa_backend/sql/004_oauth_states.sql`
- Create: `src/chiwawa_backend/sql/005_memorial_hardening.sql`
- Create: `src/chiwawa_backend/sql/006_upload_request_slots.sql`
- Test: `tests/test_database_migrations.py`
- Test: `tests/test_packaging_and_ids.py`

**Interfaces:**
- Produces `DeploymentMode`, `Settings.is_production`, `Settings.photo_dir_path()`.
- Produces `initialize_database(settings)`, `connect(settings)` and
  `current_migration_version(settings)`.

- [ ] Write failing tests proving relative photo paths resolve from runtime CWD,
  migrations run once, failed migrations do not enter the ledger, WAL/foreign keys are
  enabled, and versions 003-006 are package resources.
- [ ] Run `uv run pytest tests/test_database_migrations.py tests/test_packaging_and_ids.py -q`
  and confirm failures are caused by missing settings/ledger/resources.
- [ ] Add frozen typed settings for deployment mode, DB/photo paths, request limits,
  quota/rate/concurrency, image dimensions/pixels, and disk watermark. Add a production
  validation method that requires JWT, OAuth, secure cookie, absolute DB path, and
  absolute photo root.
- [ ] Replace per-connect script replay with a `schema_migrations(version, name,
  applied_at)` ledger. Apply each numeric SQL resource and its ledger insert under
  `BEGIN IMMEDIATE`; configure `busy_timeout`, `foreign_keys=ON`, and WAL.
- [ ] Add the singleton app-state table, OAuth state table, Memorial time/size columns,
  upload event/lease tables, indexes, and safe backfill for existing rows.
- [ ] Re-run the two targeted test files and confirm green.
- [ ] Inspect `git diff`; do not stage or commit.

### Task 2: Request-scoped persistent travel state and atomic OAuth state

**Files:**
- Create: `src/chiwawa_backend/services/state_store.py`
- Create: `src/chiwawa_backend/services/oauth_state_store.py`
- Modify: `src/chiwawa_backend/state.py`
- Modify: `src/chiwawa_backend/dependencies.py`
- Modify: `src/chiwawa_backend/main.py`
- Modify: `src/chiwawa_backend/routers/auth.py`
- Test: `tests/test_state_persistence.py`
- Test: `tests/test_oauth_state_store.py`

**Interfaces:**
- `SQLiteStateStore.transaction() -> Iterator[AppState]` loads and commits one snapshot.
- `OAuthStateStore.issue(value, expires_at)` rejects capacity without eviction.
- `OAuthStateStore.consume(value, now) -> bool` is atomic and one-shot.

- [ ] Write failing tests for complete snapshot round-trip, rollback on handler failure,
  two store instances observing the same trip, and concurrent updates without lost data.
- [ ] Write failing tests for store A issue/store B consume, exactly one successful
  concurrent consumer, expiration, purge, and capacity rejection without eviction.
- [ ] Run those test files and verify the expected process-local failures.
- [ ] Define a frozen `StateSnapshot` containing every existing collection plus
  `trip_owners` and an explicit schema version. Exclude runtime locks and stores.
- [ ] Implement the SQLite state transaction with `BEGIN IMMEDIATE`, request-local
  `AppState`, rollback, and commit before dependency teardown.
- [ ] Implement separate short OAuth transactions and wire auth login/callback to them so
  no provider HTTP call runs while the state DB write lock is held.
- [ ] Keep explicit `create_app(state)` as the in-memory test/development provider; make
  production use SQLite dependencies with `scope="function"`.
- [ ] Run targeted tests, then `uv run pytest tests/test_plan_atomicity.py
  tests/test_command_idempotency.py -q`.

### Task 3: Production JWT enforcement and trip ownership

**Files:**
- Modify: `src/chiwawa_backend/dependencies.py`
- Modify: `src/chiwawa_backend/services/common.py`
- Modify: `src/chiwawa_backend/services/trips.py`
- Modify: `src/chiwawa_backend/routers/trips.py`
- Modify: all trip-scoped routers under `src/chiwawa_backend/routers/`
- Test: `tests/test_trip_ownership.py`

**Interfaces:**
- `ActorIdDep` returns `0` in anonymous development and a numeric JWT subject in production.
- `require_trip_access` returns 404 for missing and foreign-owned trips.

- [ ] Write failing production-mode HTTP tests for no token 401, owner create/list/get,
  non-owner list filtering, non-owner direct 404, and nested route protection.
- [ ] Run the test and confirm production currently permits anonymous cross-user access.
- [ ] Record `trip_owners[trip_id]` during create, filter list by actor, check owner for
  item operations, and remove the mapping during trip cascade delete.
- [ ] Add the common trip-access dependency to every router with `{trip_id}` while keeping
  development actor compatibility.
- [ ] Run ownership tests and the existing API pipeline.

### Task 4: ASGI early authentication, body limits, and security headers

**Files:**
- Create: `src/chiwawa_backend/middleware/__init__.py`
- Create: `src/chiwawa_backend/middleware/request_security.py`
- Modify: `src/chiwawa_backend/main.py`
- Test: `tests/test_request_security.py`

**Interfaces:**
- `EarlyUploadAuthMiddleware` rejects protected multipart requests without calling receive.
- `RequestBodyLimitMiddleware` checks declared and actual bytes.
- `SecurityHeadersMiddleware` adds request ID and stable baseline headers.

- [ ] Write failing ASGI tests proving anonymous multipart returns 401 with zero body bytes
  consumed, oversized declared length returns 413 with zero bytes, and chunked input stops
  at the configured limit instead of consuming the full stream.
- [ ] Add failing tests for JSON limits and security/request-ID headers on 200, 401, 404,
  and 413 responses.
- [ ] Run the tests and confirm the current body-consumption failures.
- [ ] Implement pure ASGI middleware; never call `request.body()` and never use
  `BaseHTTPMiddleware`. Preserve one terminal response if wrapped receive raises.
- [ ] Register middleware in the order: request-ID/security outermost, early auth,
  body limit, FastAPI routes.
- [ ] Re-run targeted tests.

### Task 5: Private local photo store and upload admission

**Files:**
- Create: `src/chiwawa_backend/services/local_photo_store.py`
- Create: `src/chiwawa_backend/services/upload_admission.py`
- Modify: `src/chiwawa_backend/services/exif.py`
- Modify: `src/chiwawa_backend/services/memorial_photos.py`
- Modify: `src/chiwawa_backend/routers/memorial.py`
- Test: `tests/test_memorial_storage.py`
- Test: `tests/test_memorial_upload_security.py`

**Interfaces:**
- `LocalPhotoStore.save(user_id, suffix, data) -> relative Path`.
- `LocalPhotoStore.resolve(relative_path) -> Path` enforces root confinement.
- `LocalPhotoStore.stage_delete/restore/finalize_delete` provides trash semantics.
- `UploadAdmission` acquires/releases a heartbeat-renewed DB lease and checks
  rate/quota atomically; photo metadata commit fences on that lease.

- [ ] Write failing tests for `0700` directories, `0600` files under permissive umask,
  symlink/root escape rejection, relative DB paths, and delete failure recovery.
- [ ] Write failing tests for count/byte quota, per-user rate, global/user concurrency,
  low disk 507, and quota release after delete.
- [ ] Write failing tests that decompression-bomb warnings are rejected and a PNG declared
  as JPEG is stored/served as `image/png`.
- [ ] Run targeted tests and observe the known failures.
- [ ] Extract atomic local file operations using `os.open(... O_EXCL, 0o600)` and repair
  existing directory/file permissions.
- [ ] Implement short DB admission leases with expiry, rate events, `BEGIN IMMEDIATE`
  quota checks, and cleanup in `finally`.
- [ ] Make Pillow warning an error, enforce dimensions/pixels, and return detected MIME.
- [ ] Refactor `memorial_photos.py` into orchestration plus focused store/repository helpers,
  keeping every touched production file at or below 250 pure LOC.
- [ ] Implement durable trash hard-link -> source unlink -> DB delete -> commit ->
  best-effort trash cleanup, restoring the file on DB failure.
- [ ] Add `private, no-store` and `nosniff` to metadata/file responses.
- [ ] Run new storage/security tests and existing Memorial tests.

### Task 6: PATCH semantics and cross-trip reference integrity

**Files:**
- Modify: `src/chiwawa_backend/schemas/places.py`
- Modify: `src/chiwawa_backend/schemas/schedule.py`
- Modify: `src/chiwawa_backend/schemas/memorial.py`
- Modify: `src/chiwawa_backend/schemas/trips.py`
- Modify: `src/chiwawa_backend/services/wanted_places.py`
- Modify: `src/chiwawa_backend/services/schedule.py`
- Modify: `src/chiwawa_backend/services/memorial.py`
- Modify: `src/chiwawa_backend/services/memorial_photos.py`
- Test: `tests/test_patch_and_reference_integrity.py`

**Interfaces:**
- Omitted fields preserve values; nullable explicit null clears; required explicit null is 422.
- Schedule `place_id` always references a wanted place in the same trip.

- [ ] Write failing `{}`, explicit-null, and replacement PATCH tests for wanted place,
  schedule, trip memorial, and member photo. Include non-null null rejection and paired GPS.
- [ ] Write failing create/patch tests for missing and cross-trip `place_id`, plus a delete
  test proving schedule/plan references become null while their display snapshots remain.
- [ ] Run the new test and verify expected failures.
- [ ] Use `model_fields_set` for tri-state merges and model validators for non-null/coordinate
  invariants.
- [ ] Validate schedule place ownership on create/update and atomically null matching
  schedule/plan references plus remove confirmation caches on wanted-place delete.
- [ ] Run targeted and pipeline/plan tests.

### Task 7: Memorial time normalization and AI DTO parity

**Files:**
- Modify: `src/chiwawa_backend/services/memorial_photos.py`
- Modify: `src/chiwawa_backend/schemas/ai_planning.py`
- Modify: `src/chiwawa_backend/schemas/__init__.py`
- Test: `tests/test_memorial_time_contract.py`
- Modify: `tests/test_ai_planning_dto.py`

**Interfaces:**
- Naive/fallback photo times become `Asia/Tokyo`; rows store response time, UTC instant,
  and local date separately.
- AI status/category/route/timeline models match the current provider wire contract.

- [ ] Write failing mixed-offset UTC-order, Tokyo date-boundary, naive-time, and host-TZ
  independence tests.
- [ ] Write failing AI tests for offset/reversed time, duplicate day index/date, empty POIs,
  unknown category, invalid preferred day, `PARTIAL_SUCCESS`, and route options/timeline.
- [ ] Run both test files and confirm failures are contract gaps.
- [ ] Normalize input with `ZoneInfo("Asia/Tokyo")`, persist UTC sort keys/local dates, and
  query by explicit columns rather than ISO substr/text order.
- [ ] Add exhaustive enums and Pydantic model validators/serializers for the AI contract.
- [ ] Run targeted tests.

### Task 8: Readiness, typed errors, and exact OpenAPI contract

**Files:**
- Modify: `src/chiwawa_backend/errors.py`
- Modify: `src/chiwawa_backend/main.py`
- Modify: `src/chiwawa_backend/routers/health.py`
- Modify: all routers with runtime domain/auth/storage errors
- Modify: `tests/test_api_docs.py`
- Test: `tests/test_readiness.py`

**Interfaces:**
- `/health` is liveness; `/ready` checks DB, migrations, photo root, disk, and production config.
- Service errors map centrally to 401/404/413/415/422/429/502/503/507.

- [ ] Write failing readiness tests for valid dependencies and invalid DB/photo/config states.
- [ ] Tighten OpenAPI tests to the exact path/method set and actual Bearer/error/binary response
  matrix.
- [ ] Run tests and record missing readiness and response declarations.
- [ ] Add typed application errors and central handlers; remove FastAPI HTTP errors from
  touched service modules.
- [ ] Add router-level reusable response maps, file binary schema, and `/ready`.
- [ ] Run readiness, API docs, auth, and Memorial tests.

### Task 9: Documentation and packaging contract

**Files:**
- Modify: `.env.example`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/architecture/backend.md`
- Modify: `docs/api/auth.md`
- Modify: `docs/api/memorial.md`
- Modify: `docs/api/reference.md`
- Modify: `docs/contracts/ai-planning-dto.md`
- Modify: `sql/002_memorial_photos.sql`
- Modify: `pyproject.toml`

- [ ] Raise the FastAPI minimum to the installed function-scope dependency version and update
  the lock only if `uv lock --check` requires it.
- [ ] Document development/production behavior, single-host boundary, local paths, permissions,
  quotas, readiness, ownership, PATCH semantics, Tokyo/UTC model, and AI wire contract.
- [ ] Add `data/memorial_photos/` to Git ignore and replace the top-level duplicate SQL content
  with a canonical-source notice.
- [ ] Run `uv lock --check` and package-resource tests.

### Task 10: Full verification and manual QA

**Files:**
- Verify all changed files; no new implementation scope.

- [ ] Run the Python no-excuse audit on every changed `.py` file and measure pure LOC; split
  any production module over 250 pure LOC.
- [ ] Run `make check` and read the complete output.
- [ ] Run `uv build --wheel` and inspect wheel contents for SQL migrations.
- [ ] Install the wheel in a temporary environment and start Uvicorn from a runtime CWD.
- [ ] Live-test `/health`, `/ready`, OpenAPI, production auth/ownership, trip-plan-confirm,
  early anonymous upload rejection, authenticated photo upload/download/PATCH/delete, security
  headers, and low-level error paths.
- [ ] Start two workers/app processes sharing the same local DB, create through one, read through
  the other, and verify OAuth state is consumed exactly once across workers.
- [ ] Re-read this plan and the design spec line by line; report any residual unsupported risk.
- [ ] Inspect final `git status` and confirm the staged `../.idea/*` files remain untouched.

## Staffing recommendation

- `total_atomic_steps`: 63
- `file_independent_steps`: 5 discovery/test-writing groups before implementation
- `cross_file_dependent_steps`: 58
- `per_step_assignment`: inline deep implementation, because state/database/router changes share
  interfaces and the worktree is shared
- `dispatch_path_recommendation`: legacy/inline
- `rationale`: parallel edits would collide in `config.py`, `database.py`, `main.py`,
  `dependencies.py`, and Memorial modules; sequential red-green cycles are safer.
