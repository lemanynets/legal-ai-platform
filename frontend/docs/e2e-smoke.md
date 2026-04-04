# Playwright Smoke (Analyze + Generate + WS)

## Local run
- Start backend on `http://127.0.0.1:8000`
- Start frontend on `http://127.0.0.1:3000`
- Run:
  - `npm run e2e:install`
  - `npm run e2e:smoke`

## Optional env vars
- `PLAYWRIGHT_BASE_URL` (default: `http://127.0.0.1:3000`)
- `PLAYWRIGHT_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `E2E_AUTH_TOKEN` (default: `dev-token-demo-user`)
- `E2E_USER_ID` (default: `demo-user`)

## What it verifies
- Analyze page opens and WS status becomes `Live`
- `POST /api/notifications/emit-test` produces live event in Analyze
- Generate page opens and WS status becomes `Live`
- `POST /api/notifications/emit-test` produces live event in Generate
