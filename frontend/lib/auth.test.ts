import { login, registerUser } from "./auth";

describe("auth client", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns localized network error instead of raw fetch error", async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(registerUser("test2@counsel.com", "secret12", "Test User")).rejects.toThrow(
      "Не вдалося з'єднатися з сервером. Перевірте, чи запущено бекенд на localhost:8000.",
    );
  });

  it("preserves backend detail for login failures", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: {
        get: () => "application/json",
      },
      json: async () => ({ detail: "Неправильний email або пароль" }),
      text: async () => "",
    } as Response);

    await expect(login("user@example.com", "wrong-password")).rejects.toThrow(
      "Неправильний email або пароль",
    );
  });
});
