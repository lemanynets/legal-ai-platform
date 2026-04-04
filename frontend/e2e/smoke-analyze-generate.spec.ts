import { expect, test } from "@playwright/test";

const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || "http://127.0.0.1:8000";
const authToken = process.env.E2E_AUTH_TOKEN || "dev-token-demo-user";
const userId = process.env.E2E_USER_ID || "demo-user";

test("analyze/generate receive live WS events after emit-test", async ({ page, request }) => {
  const health = await request.get(`${apiBase}/health`).catch(() => null);
  test.skip(!health || !health.ok(), `Backend is unavailable at ${apiBase}`);

  await page.addInitScript(
    ({ token, uid }) => {
      localStorage.setItem(
        "legal_ai_session",
        JSON.stringify({
          user_id: uid,
          email: `${uid}@local.dev`,
          name: uid,
          plan: "PRO_PLUS",
          token,
        })
      );
    },
    { token: authToken, uid: userId }
  );

  await page.goto("/dashboard/analyze");
  await expect(page.getByTestId("analyze-live-panel")).toBeVisible();

  await expect
    .poll(async () => (await page.getByTestId("analyze-live-status").textContent())?.trim())
    .toBe("Live");

  const emitAnalyze = await request.post(`${apiBase}/api/notifications/emit-test`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  expect(emitAnalyze.ok()).toBeTruthy();

  await expect(page.getByTestId("analyze-live-events")).toContainText("Тестове сповіщення");

  await page.goto("/dashboard/generate");
  await expect(page.getByTestId("generate-live-panel")).toBeVisible();
  await expect
    .poll(async () => (await page.getByTestId("generate-live-status").textContent())?.trim())
    .toBe("Live");

  const emitGenerate = await request.post(`${apiBase}/api/notifications/emit-test`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  expect(emitGenerate.ok()).toBeTruthy();

  await expect(page.getByTestId("generate-live-events")).toContainText("Тестове сповіщення");
});
