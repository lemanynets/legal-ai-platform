"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function Redirect() {
  const router = useRouter();
  const sp = useSearchParams();
  useEffect(() => {
    const extra = sp.toString();
    router.replace(`/dashboard/analyze?mode=litigation${extra ? "&" + extra : ""}`);
  }, [router, sp]);
  return (
    <div style={{ padding: "24px", color: "var(--text-secondary)" }}>
      Переходимо до AI Аналіз — Судовий...
    </div>
  );
}

export default function FullLawyerPage() {
  return <Suspense><Redirect /></Suspense>;
}
