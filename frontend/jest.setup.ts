import "@testing-library/jest-dom";

import { TextDecoder, TextEncoder } from "util";

type HeaderMap = Record<string, string>;

class HeadersPolyfill {
  private readonly values: Map<string, string>;

  constructor(init?: HeaderMap | Array<[string, string]>) {
    this.values = new Map<string, string>();
    if (Array.isArray(init)) {
      init.forEach(([key, value]) => this.set(key, value));
      return;
    }
    if (init) {
      Object.entries(init).forEach(([key, value]) => this.set(key, value));
    }
  }

  get(name: string): string | null {
    return this.values.get(name.toLowerCase()) ?? null;
  }

  set(name: string, value: string): void {
    this.values.set(name.toLowerCase(), String(value));
  }
}

class ResponsePolyfill {
  readonly status: number;
  readonly headers: HeadersPolyfill;
  readonly ok: boolean;
  private readonly bodyText: string;

  constructor(body?: string | null, init?: { status?: number; headers?: HeaderMap | Array<[string, string]> }) {
    this.status = init?.status ?? 200;
    this.headers = new HeadersPolyfill(init?.headers);
    this.ok = this.status >= 200 && this.status < 300;
    this.bodyText = body ?? "";
  }

  async json(): Promise<unknown> {
    return JSON.parse(this.bodyText || "{}");
  }

  async text(): Promise<string> {
    return this.bodyText;
  }
}

const globalAny = globalThis as any;

if (!globalAny.TextEncoder) {
  globalAny.TextEncoder = TextEncoder;
}
if (!globalAny.TextDecoder) {
  globalAny.TextDecoder = TextDecoder;
}
if (!globalAny.Headers) {
  globalAny.Headers = HeadersPolyfill;
}
if (!globalAny.Response) {
  globalAny.Response = ResponsePolyfill;
}
if (!globalAny.fetch) {
  globalAny.fetch = jest.fn(async () => {
    throw new Error("Global fetch is not mocked for this test.");
  });
}

const navigationMock = {
  push: jest.fn(),
  replace: jest.fn(),
  refresh: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  prefetch: jest.fn(),
};

jest.mock("next/navigation", () => ({
  useRouter: () => navigationMock,
  usePathname: () => "/dashboard",
  useSearchParams: () => ({
    get: () => null,
    has: () => false,
    toString: () => "",
  }),
}));
