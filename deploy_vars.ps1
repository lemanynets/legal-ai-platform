$backendVars = @(
  "OPENAI_API_KEY=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",
  "GEMINI_API_KEY=AIzaSyCWhmN0swLVl4BGHtHBxQliEE-VxRk4zAs",
  "ANTHROPIC_API_KEY=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",
  "ALLOW_DEV_AUTH=true",
  "ALLOWED_ORIGINS=https://frontend-production-46a0.up.railway.app",
  "DATABASE_URL=${{Postgres.DATABASE_URL}}"
)

foreach ($var in $backendVars) {
  Write-Host "Setting $var for backend..."
  railway variable set $var -s backend --skip-deploys
}

$frontendVars = @(
  "NEXT_PUBLIC_API_BASE_URL=https://backend-production-0e53.up.railway.app",
  "NEXT_PUBLIC_ALLOW_DEV_AUTH=true"
)

foreach ($var in $frontendVars) {
  Write-Host "Setting $var for frontend..."
  railway variable set $var -s frontend --skip-deploys
}
