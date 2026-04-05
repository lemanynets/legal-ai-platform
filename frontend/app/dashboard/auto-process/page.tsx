"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function Redirect() {
  const router = useRouter();
  const sp = useSearchParams();
  useEffect(() => {
    const extra = sp.toString();
    router.replace(`/dashboard/generate?mode=package${extra ? "&" + extra : ""}`);
  }, [router, sp]);
  return (
    <div style={{ padding: "24px", color: "var(--text-secondary)" }}>
      Переходимо до Генерація — Пакет...
    </div>
  );
}

export default function AutoProcessPage() {
  return <Suspense><Redirect /></Suspense>;
}
