import { render, screen } from "@testing-library/react";

import ChromeBoundary from "./ChromeBoundary";

const usePathnameMock = jest.fn();

jest.mock("next/navigation", () => ({
  usePathname: () => usePathnameMock(),
}));

jest.mock("./AppShell", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="app-shell">{children}</div>,
}));

describe("ChromeBoundary", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders public routes without AppShell", () => {
    usePathnameMock.mockReturnValue("/login");

    render(<ChromeBoundary><div>Public content</div></ChromeBoundary>);

    expect(screen.getByText("Public content")).toBeInTheDocument();
    expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
  });

  it("renders dashboard routes inside AppShell", () => {
    usePathnameMock.mockReturnValue("/dashboard");

    render(<ChromeBoundary><div>Private content</div></ChromeBoundary>);

    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByText("Private content")).toBeInTheDocument();
  });
});
