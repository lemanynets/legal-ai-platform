"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function StrategyStudioPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard/analyze?mode=litigation");
  }, [router]);
  return (
    <div style={{ padding: "24px", color: "var(--text-secondary)" }}>
      Переходимо до AI Аналіз — Судовий...
    </div>
  );
}
