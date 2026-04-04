# Frontend Lint Cleanup Waves

## Scope policy
- Run lint cleanup in a dedicated PR only.
- Do not mix lint-only edits with feature or bugfix changes.

## Wave 1 (safe autofix)
- Command: `npm run lint:fix:wave1`
- Target:
  - `react/no-unescaped-entities`
  - formatting-only ESLint autofixes

## Wave 2 (hook dependencies)
- Command: `npm run lint:wave2:hooks`
- Target:
  - `react-hooks/exhaustive-deps`

## Validation gates
- `npm run lint`
- `npm run typecheck`
- `npm test -- --ci --watchAll=false`
