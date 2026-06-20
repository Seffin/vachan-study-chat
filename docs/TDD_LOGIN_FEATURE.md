# TDD: Login Feature

## Overview

TDD strategy for adding JWT-based authentication to Vachan Study. Follows **Red → Green → Refactor**.

**Status: ✅ Fully implemented and deployed to production.**

## Requirements

### Functional
- Login with username/password returns a JWT
- Passwords hashed with bcrypt (never plain text)
- 401 on invalid credentials
- Rate limit: 5 failed attempts / 15 min
- One active session per user

### Non-Functional
- Response < 200ms
- Token expires in 24h
- Password minimum 8 characters
- Login attempts logged for audit

---

## Backend Tests (`backend/tests/test_auth.py`)

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| `test_login_valid` | Correct credentials | JWT + user info | 200 |
| `test_login_invalid_password` | Wrong password | Error message | 401 |
| `test_login_nonexistent_user` | Unknown username | Error message | 401 |
| `test_token_format` | Valid token shape | JWT with expiry claim | 200 |
| `test_token_expiration` | Token lifetime | Expires in 24h | 200 |
| `test_empty_credentials` | Empty fields | Validation error | 400 |
| `test_rate_limiting` | 5+ failed attempts | Blocked | 429 |

### What These Validate
- Input validation, auth logic, response format, security claims, rate limiting

---

## Frontend Tests (`src/__tests__/LoginForm.test.tsx`)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_renders_form` | Component loads | Inputs + submit button visible |
| `test_submits_credentials` | Valid input | POST to `/api/auth/login` |
| `test_shows_success` | Login OK | Success feedback + redirect |
| `test_shows_error` | Login fails | Error message visible |
| `test_loading_state` | Request in flight | Button disabled + spinner |
| `test_empty_validation` | Empty submit | Validation errors before API |
| `test_stores_token` | Success | Token saved to `localStorage` |

### What These Validate
- UI rendering, user interaction, API wiring, state handling, error UX, navigation

---

## Green Phase: Implementation (Complete)

### Backend (✅ All Done)
1. ✅ `users` MongoDB collection (username unique indexed, `password_hash` via bcrypt)
2. ✅ `POST /api/auth/login` endpoint (Pydantic `LoginRequest` model)
3. ✅ Query user by username → bcrypt verify → JWT sign with `session_id`
4. ✅ Return 401 on mismatch, 429 on rate limit
5. ✅ `POST /api/auth/register` endpoint with duplicate username check
6. ✅ `GET /api/auth/me` endpoint with JWT bearer token validation
7. ✅ `POST /api/auth/logout` endpoint (clears `session_id`)
8. ✅ Login audit logging to `login_audit` MongoDB collection
9. ✅ Single-session enforcement: `session_id` in JWT must match DB value

### Frontend (✅ All Done)
1. ✅ `LoginPage` component with username/password inputs
2. ✅ Form state (values, loading, error)
3. ✅ POST credentials to backend
4. ✅ Feedback: loading spinner, error banner, success redirect
5. ✅ Store JWT in `localStorage` (`vachan-auth-token`)
6. ✅ Token validation on mount via `/api/auth/me`
7. ✅ Global logout handler clearing token and session

---

## Refactor Targets

| Area | From | To | Status |
|------|------|-----|--------|
| Backend repository | Logic in endpoint | `UserRepository` class | ✅ Done |
| Backend service | Auth in endpoint | `app/core/security.py` abstraction | ✅ Done |
| Backend errors | Generic strings | Structured JSON error responses | ✅ Done |
| Backend validation | Manual checks | Pydantic validators | ✅ Done |
| Backend secrets | Hardcoded | Environment variables (`SECRET_KEY`) | ✅ Done |
| Backend rate limiting | None | In-memory rate limiter (5 attempts / 15 min) | ✅ Done |
| Backend auditing | None | `login_audit` MongoDB collection | ✅ Done |
| Frontend state | `useState` hooks | `useState` (kept simple, sufficient) | ✅ Done |
| Frontend storage | `localStorage` | `localStorage` with token validation on mount | ✅ Done |

---

## Success Criteria

- **Red:** ✅ All tests written and failing
- **Green:** ✅ All tests passing with minimal code
- **Refactor:** ✅ All tests still passing after cleanup + security hardening

---

## Dependencies

- **Backend:** `pytest`, `pytest-asyncio`, `httpx`, `bcrypt`, `pyjwt`
- **Frontend:** `jest`, `@testing-library/react`, `@testing-library/user-event`

---

## Implementation Files

| File | Purpose |
|------|--------|
| `backend/api/index.py` | Auth endpoints (login, register, logout, me) |
| `backend/app/core/security.py` | JWT creation/decode, bcrypt, rate limiting |
| `backend/app/core/config.py` | Pydantic settings (SECRET_KEY, token expiry) |
| `backend/db/user_repository.py` | User CRUD, session management |
| `src/components/LoginPage.tsx` | Login/Register UI component |
| `src/app/page.tsx` | Auth state management, token validation |

---

## Production Status

✅ Deployed to Vercel with all auth features live. Single-session enforcement ensures that logging in on a new device automatically invalidates the previous session. Login attempts are audited in MongoDB.
