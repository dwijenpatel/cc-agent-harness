---
type: Spec
title: "GL2-auth-tenancy — signup, login, sessions, CSRF, tenant scoping"
description: "greenlane is a **multi-tenant** SaaS for small landscaping companies built on"
timestamp: 2026-07-14
---

# GL2-auth-tenancy — signup, login, sessions, CSRF, tenant scoping

## Context

greenlane is a **multi-tenant** SaaS for small landscaping companies built on
FastAPI + Jinja2 + SQLAlchemy/SQLite (scaffold exists: `create_app()` in
`pilot/greenlane/app/__init__.py`, `get_db`, `Base`, templates, test
fixtures). This task is the trust-critical core: company signup, email+password
login, server-side sessions, CSRF protection, and the tenant-scoping helpers
**every later route depends on**. Two roles exist: `owner` and `crew` (crew
accounts are created by a later invites task — but the role enforcement
helpers land here).

## Models (add to `app/models.py`)

- `Company`: `id` (int PK), `name` (str, non-empty), `timezone` (str, valid
  IANA name, e.g. `America/New_York`), `created_at` (UTC datetime).
- `User`: `id`, `company_id` (FK, indexed), `email` (str, stored lowercase),
  `password_hash` (str, bcrypt via passlib), `role` (str: `owner`|`crew`),
  `name` (str), `created_at`. Unique constraint on (`company_id`, `email`);
  **email is also globally unique** across companies (login is by email
  alone).

## Session & security plumbing (`app/security.py`)

- Starlette `SessionMiddleware` with `GREENLANE_SECRET`, cookie name
  `gl_session`, `https_only=False`, `same_site="lax"` (httponly is the
  middleware default). Session payload: `{"user_id": <int>}` only.
- `hash_password` / `verify_password` (passlib bcrypt).
- `current_user(request, db)` dependency: reads `user_id` from the session,
  loads the User; no/invalid session → redirect `303` to `/login` for HTML
  routes.
- `require_owner(user)` dependency wrapper: user.role != owner → **403**.
- Tenant scoping: `company_query(db, Model, user)` / `get_or_404(db, Model,
  id, user)` helpers that ALWAYS filter by `Model.company_id ==
  user.company_id`. `company_id` must NEVER be read from request params.
  A same-type object belonging to another company → **404** (uniform with
  nonexistent; never 403, never a redirect).
- CSRF: on first need, generate `csrf_token` (`secrets.token_urlsafe(32)`)
  into the session; template helper injects
  `<input type="hidden" name="csrf_token" ...>` into every form; every
  POST handler validates the field against the session value → mismatch or
  absence is **400**. Provide `check_csrf(request, form)` used by all later
  tasks.

## Routes (in `app/routes/auth.py` — this path is floored critical; do not put these handlers anywhere else)

- `GET /signup` — form: company name, IANA timezone (`<select>` from
  `zoneinfo.available_timezones()`, default `America/New_York`), your name,
  email, password (min 8 chars).
- `POST /signup` — validates (duplicate email → re-render form with error,
  200; bad timezone/short password → same), then creates Company + owner
  User, logs them in (session), redirects 303 → `/`.
- `GET /login`, `POST /login` — email+password; wrong either → re-rendered
  form with a single generic error, 200. Success → session set, 303 → `/`.
- `POST /logout` — CSRF-checked; clears session; 303 → `/login`.
- `GET /settings` (owner only) — edit company name + timezone;
  `POST /settings` saves, re-renders with confirmation.
- `GET /` — authenticated placeholder page showing company name and the
  user's role (later tasks replace it); unauthenticated → 303 `/login`.

**Standing invariant:** the project is typed strict on both sides — mypy config is pinned in `pilot/greenlane/pyproject.toml` and strict JSDoc/tsc config in `pilot/greenlane/tsconfig.json`. Fully annotate all new application code: `python -m mypy app` and `npm run typecheck` (both from `pilot/greenlane/`) must stay at zero errors; any `.js` you add under `app/static/` must be JSDoc-typed.

## Acceptance criteria

1. Signup creates exactly one Company and one owner User; password stored
   bcrypt-hashed (starts `$2`), never plaintext anywhere.
2. Full cycle signup → logout → login works through TestClient.
3. Two companies signed up in one DB: user A's session with a request for a
   company-B object id (any helper-using route) yields 404. (Held-out tests
   will attack this on every later surface; the helpers must make scoping the
   default, not an option.)
4. Any mutating POST without a valid `csrf_token` field → 400, no state
   change.
5. `GET /settings` as crew role → 403; unauthenticated `GET /` → 303 to
   `/login`.
6. Duplicate-email signup and wrong-password login both re-render with an
   error and create/mutate nothing.

## Non-goals

No invites (GL3), no password reset, no rate limiting, no 2FA, no email
verification. No customer/schedule models. Do not touch anything outside
`pilot/greenlane/`.
