"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AutoProcessPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard/generate?mode=package");
  }, [router]);
  return (
    <div style={{ padding: "24px", color: "var(--text-secondary)" }}>
      Переходимо до Генерація — Пакет...
    </div>
  );
}
