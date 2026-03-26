"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import AppShell from "./AppShell";

const PUBLIC_PATHS = new Set(["/", "/login"]);

export default function ChromeBoundary({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const safePath = pathname || "/";

  if (PUBLIC_PATHS.has(safePath)) {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}
