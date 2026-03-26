"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const FEATURES = [
  {
    icon: "AI",
    title: "AI-генерація документів",
    description:
      "Позови, клопотання, договори та процесуальні заяви з готовим DOCX/PDF-експортом."
  },
  {
    icon: "FL",
    title: "Повний юрист",
    description:
      "Один запуск для аналізу справи, ризиків, позиції опонента та пакета наступних дій."
  },
  {
    icon: "SP",
    title: "Судова практика",
    description:
      "Пошук релевантних позицій Верховного Суду та підбір практики для підсилення аргументації."
  },
  {
    icon: "RC",
    title: "Реєстри та моніторинг",
    description:
      "Перевірка контрагентів, спостереження за змінами та сигнали по критичних подіях."
  },
  {
    icon: "EC",
    title: "Е-суд та календар",
    description:
      "Робота з засіданнями, синхронізація календаря та підготовка матеріалів без ручного хаосу."
  },
  {
    icon: "CL",
    title: "Калькулятори та строки",
    description:
      "Швидкі розрахунки збору, пені, штрафів та контроль дедлайнів у поточній роботі."
  }
];

const PLANS = [
  {
    name: "Standard",
    price: "0",
    period: "грн",
    description: "Для старту і тестового використання",
    features: ["Базові шаблони", "PDF / DOCX експорт", "Калькулятори"],
    cta: "Почати",
    href: "/login",
    featured: false
  },
  {
    name: "PRO",
    price: "990",
    period: "грн / міс",
    description: "Основний робочий режим для юриста",
    features: ["AI-генерація", "Судова практика", "Аналіз рішень"],
    cta: "Обрати PRO",
    href: "/login",
    featured: true
  },
  {
    name: "PRO+",
    price: "1990",
    period: "грн / міс",
    description: "Для повного циклу роботи зі справами",
    features: ["Е-суд", "Реєстровий моніторинг", "Командна робота"],
    cta: "Обрати PRO+",
    href: "/login",
    featured: false
  }
];

export default function HomePage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 16);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        color: "#f8fafc",
        background:
          "radial-gradient(circle at top right, rgba(212,168,67,0.16), transparent 32%), radial-gradient(circle at bottom left, rgba(37,99,235,0.18), transparent 38%), linear-gradient(180deg, #08111f 0%, #050b14 100%)"
      }}
    >
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 5%",
          background: scrolled ? "rgba(5,11,20,0.82)" : "transparent",
          backdropFilter: scrolled ? "blur(18px)" : "none",
          borderBottom: scrolled ? "1px solid rgba(255,255,255,0.08)" : "none",
          transition: "all 0.25s ease"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "linear-gradient(135deg, #d4a843, #f3d98d)",
              color: "#111827",
              fontWeight: 900
            }}
          >
            LA
          </div>
          <div>
            <div style={{ fontWeight: 800, letterSpacing: "-0.03em" }}>LEGAL AI</div>
            <div style={{ fontSize: 12, color: "rgba(248,250,252,0.58)" }}>
              Платформа для щоденної юридичної роботи
            </div>
          </div>
        </div>

        <nav style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <a href="#features" style={{ color: "rgba(248,250,252,0.7)", fontSize: 14 }}>
            Можливості
          </a>
          <a href="#pricing" style={{ color: "rgba(248,250,252,0.7)", fontSize: 14 }}>
            Тарифи
          </a>
          <Link href="/login" className="btn btn-primary" style={{ height: 42, padding: "0 22px" }}>
            Увійти
          </Link>
        </nav>
      </header>

      <main style={{ position: "relative", zIndex: 1 }}>
        <section
          style={{
            maxWidth: 1240,
            margin: "0 auto",
            padding: "96px 5% 72px",
            textAlign: "center"
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              padding: "8px 18px",
              borderRadius: 999,
              border: "1px solid rgba(212,168,67,0.28)",
              background: "rgba(212,168,67,0.08)",
              color: "#f3d98d",
              fontSize: 13,
              fontWeight: 700,
              marginBottom: 28
            }}
          >
            Правова робота без зайвих ручних кроків
          </div>

          <h1
            style={{
              maxWidth: 980,
              margin: "0 auto 24px",
              fontSize: "clamp(40px, 6vw, 78px)",
              lineHeight: 1,
              letterSpacing: "-0.05em",
              fontWeight: 900
            }}
          >
            Юридичний AI-асистент для документів, практики, моніторингу та е-суду
          </h1>

          <p
            style={{
              maxWidth: 760,
              margin: "0 auto 40px",
              color: "rgba(248,250,252,0.66)",
              fontSize: 19,
              lineHeight: 1.6
            }}
          >
            Платформа збирає в одному місці генерацію документів, аналіз контрактів,
            судову практику, календар справ, роботу з реєстрами та керування підпискою.
          </p>

          <div style={{ display: "flex", justifyContent: "center", gap: 16, flexWrap: "wrap" }}>
            <Link href="/login" className="btn btn-primary" style={{ padding: "18px 32px" }}>
              Почати роботу
            </Link>
            <a href="#pricing" className="btn btn-secondary" style={{ padding: "18px 32px" }}>
              Переглянути тарифи
            </a>
          </div>

          <div
            style={{
              marginTop: 68,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 18
            }}
          >
            {[
              ["Генерація", "Позови, заяви, договори"],
              ["Моніторинг", "Реєстри та сигнали"],
              ["Е-суд", "Справи, засідання, календар"],
              ["PRO+", "Розширені інструменти"]
            ].map(([title, subtitle]) => (
              <div
                key={title}
                style={{
                  borderRadius: 22,
                  padding: "22px 20px",
                  textAlign: "left",
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: "rgba(255,255,255,0.03)"
                }}
              >
                <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>{title}</div>
                <div style={{ color: "rgba(248,250,252,0.58)", lineHeight: 1.5 }}>{subtitle}</div>
              </div>
            ))}
          </div>
        </section>

        <section id="features" style={{ maxWidth: 1240, margin: "0 auto", padding: "28px 5% 84px" }}>
          <div style={{ marginBottom: 36 }}>
            <div style={{ color: "#f3d98d", fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
              Можливості
            </div>
            <h2 style={{ fontSize: "clamp(30px, 4vw, 48px)", lineHeight: 1.05, marginBottom: 12 }}>
              Весь робочий контур юриста в одній панелі
            </h2>
            <p style={{ maxWidth: 760, color: "rgba(248,250,252,0.62)", lineHeight: 1.6 }}>
              Від першого запиту до фінального документа і контролю наступних дій по справі.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 20
            }}
          >
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                style={{
                  borderRadius: 24,
                  padding: 28,
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: "linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
                  boxShadow: "0 18px 48px rgba(0,0,0,0.18)"
                }}
              >
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 16,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 18,
                    background: "rgba(212,168,67,0.12)",
                    color: "#f3d98d",
                    fontWeight: 800
                  }}
                >
                  {feature.icon}
                </div>
                <h3 style={{ fontSize: 20, marginBottom: 12 }}>{feature.title}</h3>
                <p style={{ color: "rgba(248,250,252,0.62)", lineHeight: 1.6 }}>{feature.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="pricing" style={{ maxWidth: 1240, margin: "0 auto", padding: "0 5% 110px" }}>
          <div style={{ marginBottom: 36 }}>
            <div style={{ color: "#f3d98d", fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
              Тарифи
            </div>
            <h2 style={{ fontSize: "clamp(30px, 4vw, 48px)", lineHeight: 1.05, marginBottom: 12 }}>
              Оберіть план під ваш формат роботи
            </h2>
            <p style={{ maxWidth: 760, color: "rgba(248,250,252,0.62)", lineHeight: 1.6 }}>
              Стандартний старт, робочий PRO і розширений PRO+ для повного контуру ведення справ.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 20
            }}
          >
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                style={{
                  borderRadius: 28,
                  padding: 30,
                  border: plan.featured
                    ? "2px solid rgba(212,168,67,0.45)"
                    : "1px solid rgba(255,255,255,0.08)",
                  background: plan.featured ? "rgba(212,168,67,0.08)" : "rgba(255,255,255,0.03)",
                  boxShadow: plan.featured ? "0 24px 70px rgba(212,168,67,0.1)" : "none"
                }}
              >
                <div
                  style={{
                    display: "inline-flex",
                    padding: "6px 12px",
                    borderRadius: 999,
                    background: plan.featured ? "rgba(5,11,20,0.5)" : "rgba(255,255,255,0.06)",
                    color: plan.featured ? "#f3d98d" : "rgba(248,250,252,0.7)",
                    fontSize: 12,
                    fontWeight: 700,
                    marginBottom: 18
                  }}
                >
                  {plan.name}
                </div>

                <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10 }}>
                  <span style={{ fontSize: 42, fontWeight: 900 }}>{plan.price}</span>
                  <span style={{ color: "rgba(248,250,252,0.58)" }}>{plan.period}</span>
                </div>

                <p style={{ color: "rgba(248,250,252,0.64)", lineHeight: 1.6, minHeight: 52 }}>
                  {plan.description}
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: 12, margin: "24px 0 28px" }}>
                  {plan.features.map((feature) => (
                    <div key={feature} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <span style={{ color: "#34d399", fontWeight: 800 }}>+</span>
                      <span style={{ color: "rgba(248,250,252,0.84)" }}>{feature}</span>
                    </div>
                  ))}
                </div>

                <Link
                  href={plan.href}
                  className={plan.featured ? "btn btn-primary" : "btn btn-secondary"}
                  style={{ width: "100%", padding: "16px 18px", justifyContent: "center" }}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer
        style={{
          maxWidth: 1240,
          margin: "0 auto",
          padding: "0 5% 48px",
          display: "flex",
          justifyContent: "space-between",
          gap: 18,
          flexWrap: "wrap",
          color: "rgba(248,250,252,0.54)"
        }}
      >
        <div>© 2026 LEGAL AI. Платформа для щоденної юридичної роботи.</div>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          <span>Публічна оферта</span>
          <span>Політика конфіденційності</span>
          <span>Підтримка</span>
        </div>
      </footer>
    </div>
  );
}
