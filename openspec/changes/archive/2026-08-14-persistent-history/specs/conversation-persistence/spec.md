# Delta: Persistent History (Turso Migration)

> **Change**: `2026-08-14-persistent-history`
> **Modifies**: `openspec/specs/conversation-persistence/spec.md`

## Purpose

Migrate conversation history storage from a local SQLite file on HF Spaces' ephemeral disk to a remote Turso database (libSQL, SQLite-compatible). Only the connection target changes; schema, queries, lifecycle, history injection, and deletion endpoints are unchanged. This eliminates the history loss when the HF Space sleeps (~48h inactivity → ephemeral disk wipe), previously accepted in AGENTS.md §7 decision #12.

## Modified Capabilities

### Capability: conversation-persistence

Deltas against `openspec/specs/conversation-persistence/spec.md`. Requirements not listed here are unchanged.

## MODIFIED Requirements

### Requirement: Database file location and writability

The conversation history SHALL be persisted in a Turso database (libSQL, SQLite-compatible) when both `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set, connecting via the libSQL driver. When both are unset, the backend SHALL fall back to local SQLite at `SQLITE_PATH` (default `./data/historial.db`) — dev convenience only. The schema SHALL be created on first connection via `CREATE TABLE IF NOT EXISTS` (idempotent). The connection SHALL be established on first request and reused (not re-opened per request). On Turso failure (network or auth error), the backend SHALL return HTTP 503 with a user-friendly Spanish message; the frontend SHALL display it and suggest retrying.

(Previously: SQLite file at `SQLITE_PATH` on local/ephemeral disk; directory auto-created on boot; persistence across HF sleep NOT guaranteed. Now: Turso remote DB when credentials present; local SQLite is dev-only; survives sleep.)

#### Scenario: Turso connection is established on first request

- GIVEN the backend booted with `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` set
- WHEN it receives its first request after deploy
- THEN a libSQL connection is established and the schema is verified (`CREATE TABLE IF NOT EXISTS` succeeds)
- AND the connection is reused across requests (not re-opened per request)

#### Scenario: Local SQLite fallback when Turso vars are unset

- GIVEN neither `TURSO_DATABASE_URL` nor `TURSO_AUTH_TOKEN` is set
- WHEN the backend boots
- THEN it connects to local SQLite at `SQLITE_PATH` (default `./data/historial.db`)
- AND this path is dev-only, not production

#### Scenario: Turso connection failure returns 503

- GIVEN the Turso env vars are set but Turso is unreachable (network or auth error)
- WHEN the backend receives a request that requires the database
- THEN it responds HTTP 503 with a user-friendly Spanish message
- AND no partial or fabricated assistant message is returned

#### Scenario: Turso service disruption mid-request

- GIVEN a request is in flight and the Turso connection drops mid-operation
- WHEN the database operation raises a connection error
- THEN the backend responds HTTP 503 with a user-friendly Spanish message
- AND the frontend shows the error and suggests retry

## ADDED Requirements

### Requirement: Turso credentials required in production deployment

When deployed to Hugging Face Spaces, the backend MUST have both `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` configured as Space Secrets. Local SQLite (`SQLITE_PATH`) SHALL NOT be used in production. This is documented in AGENTS.md §7 and enforced by deployment config — the connection factory stays permissive so local dev works without a Turso account.

#### Scenario: HF Spaces Secrets are set for production

- GIVEN the backend is deployed to HF Spaces
- WHEN the Space boots
- THEN both Turso env vars are present as Secrets
- AND it connects to Turso (local SQLite fallback never runs)

#### Scenario: Missing Turso Secrets in production is a deploy misconfiguration

- GIVEN the backend is deployed to HF Spaces but Turso Secrets are not set
- WHEN the Space boots
- THEN it falls back to local SQLite but history is lost on sleep
- AND this is flagged as a misconfiguration in AGENTS.md, not a runtime error

## REMOVED Scenarios

### Scenario: Directory is auto-created (from "Database file location and writability")

(Reason: Turso is remote; no local directory is needed when Turso credentials are set. The local-SQLite fallback still auto-creates its own directory, but that is dev-only.)
(Migration: None — the MODIFIED requirement above replaces it.)
