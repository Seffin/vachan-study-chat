# TDD: Login Feature

## Overview

TDD strategy for adding JWT-based authentication to Vachan Study. Follows **Red → Green → Refactor**.

---

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

## Green Phase: Minimal Implementation Order

### Backend
1. `users` MongoDB collection (username unique indexed)
2. `POST /api/auth/login` endpoint (Pydantic request model)
3. Query user by username → bcrypt verify → JWT sign
4. Return 401 on mismatch

### Frontend
1. `LoginForm` component with username/password inputs
2. Form state (values, loading, error)
3. POST credentials to backend
4. Feedback: loading spinner, error banner, success redirect
5. Store JWT in `localStorage`

### Explicitly Deferred to Refactor
- Rate limiting, multilingual errors, token refresh, registration, advanced security

---

## Refactor Targets

| Area | From | To |
|------|------|-----|
| Backend repository | Logic in endpoint | `UserRepository` class |
| Backend service | Auth in endpoint | `AuthService` abstraction |
| Backend errors | Generic strings | Translatable error codes |
| Backend validation | Manual checks | Pydantic validators |
| Backend secrets | Hardcoded | Environment variables |
| Frontend state | `useState` hooks | `useReducer` if complex |
| Frontend A11y | Basic HTML | Full ARIA + keyboard |
| Frontend storage | `localStorage` | Secure storage strategy |

---

## Success Criteria

- **Red:** All tests written and failing
- **Green:** All tests passing with minimal code
- **Refactor:** All tests still passing after cleanup + security hardening

---

## Dependencies

- **Backend:** `pytest`, `pytest-asyncio`, `httpx`, `bcrypt`, `pyjwt`
- **Frontend:** `jest`, `@testing-library/react`, `@testing-library/user-event`

---

## Next Steps

1. Write tests (Red)
2. Run and confirm failures
3. Implement minimal code (Green)
4. Run and confirm passes
5. Refactor with safety net
