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

    await expect(registerUser("test2@counsel.com", "secret12", "Test User")).rejects.toThrow(/localhost:8000/);
  });

  it("preserves backend detail for login failures", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      new Response('{"detail":"Invalid credentials"}', {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    await expect(login("test2@counsel.com", "bad-password")).rejects.toThrow("Invalid credentials");
  });
});
