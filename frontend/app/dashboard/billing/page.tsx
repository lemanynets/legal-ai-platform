"use client";

import { useEffect, useState } from "react";
import { getToken, getUserId, updateSessionPlan } from "@/lib/auth";
import {
  type BillingPlan,
  type SubscriptionResponse,
  getBillingPlans,
  getCurrentSubscription,
  subscribePlan,
  updateUserInfo,
} from "@/lib/api";
import LogoUpload from "@/app/components/LogoUpload";

const PLAN_LABELS: Record<string, string> = {
  FREE: "Standard",
  PRO: "Professional",
  PRO_PLUS: "Enterprise",
};

const PLAN_FEATURES: Record<string, string[]> = {
  FREE: ["5 документів / міс", "Базові шаблони", "PDF та DOCX експорт", "Судові калькулятори"],
  PRO: ["50 документів / міс", "AI-генерація документів", "Судова практика ВС", "Аналіз контрактів", "Версії документів"],
  PRO_PLUS: ["Необмежена генерація", "Реєстровий моніторинг", "E-Court API подача", "Повний юрист (AI)", "Командний доступ", "White-labelिंग (логотип)"],
};

export default function BillingPage() {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const [liqpayForm, setLiqpayForm] = useState<{ url: string; data: string; sig: string } | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");

  useEffect(() => {
    const token = getToken();
    const userId = getUserId();
    Promise.all([
      getBillingPlans().catch(() => []),
      getCurrentSubscription(token, userId).catch(() => null),
    ]).then(([p, s]) => {
      setPlans(p);
      setSubscription(s);
      if (s?.plan) {
        updateSessionPlan(s.plan);
      }
    }).finally(() => setLoading(false));
  }, []);

  async function handleSubscribe(planCode: string) {
    if (planCode === subscription?.plan) return;
    setError("");
    setInfo("");
    setSubscribing(planCode);
    try {
      const res = await subscribePlan(planCode, "subscription", getToken(), getUserId());
      setInfo(res.message);
      if (res.liqpay_checkout_url && res.liqpay_data && res.liqpay_signature) {
        setLiqpayForm({ url: res.liqpay_checkout_url, data: res.liqpay_data, sig: res.liqpay_signature });
      } else {
        const sub = await getCurrentSubscription(getToken(), getUserId()).catch(() => null);
        if (sub?.plan) {
          updateSessionPlan(sub.plan);
        } else {
          updateSessionPlan(planCode);
        }
        setSubscription(sub);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubscribing(null);
    }
  }

  const currentPlan = subscription?.plan ?? "FREE";

  if (loading) return (
    <div className="loading-overlay">
       <div className="premium-spinner"></div>
       <p className="mt-4 text-muted uppercase tracking-widest text-xs">Завантаження тарифів...</p>
    </div>
  );

  return (
    <div className="billing-luxury-container animate-fade-in">
      <div className="section-header-centered">
        <h1 className="luxury-title">Тарифи та Підписки</h1>
        <p className="luxury-subtitle">Масштабуйте вашу юридичну практику за допомогою інтелектуальних інструментів AI.</p>
        
        <div className="billing-toggle mt-8">
          <button className={billingCycle === 'monthly' ? 'active' : ''} onClick={() => setBillingCycle('monthly')}>Щомісячно</button>
          <button className={billingCycle === 'annual' ? 'active' : ''} onClick={() => setBillingCycle('annual')}>Щорічно <span className="save-badge">-20%</span></button>
        </div>
      </div>

      {info && <div className="alert-premium success animate-slide-up">{info}</div>}
      {error && <div className="alert-premium danger animate-slide-up">{error}</div>}

      {/* Pricing Grid */}
      <div className="pricing-grid-luxury mt-12">
        {plans.map((plan) => {
          const isCurrent = plan.code === currentPlan;
          const isPro = plan.code === "PRO";
          const isEnterprise = plan.code === "PRO_PLUS";
          const price = billingCycle === 'annual' ? Math.round(plan.price_usd * 41 * 0.8) : Math.round(plan.price_usd * 41);
          
          return (
            <div key={plan.code} className={`plan-card-luxury ${isPro ? 'featured' : ''} ${isCurrent ? 'active' : ''}`}>
              {isPro && <div className="featured-ribbon">РЕКОМЕНДОВАНО</div>}
              
              <div className="plan-header">
                <div className="plan-icon">
                   {plan.code === 'FREE' ? '🌱' : plan.code === 'PRO' ? '⚖️' : '🏛️'}
                </div>
                <h3>{PLAN_LABELS[plan.code] || plan.code}</h3>
                <div className="plan-price">
                  <span className="currency">₴</span>
                  <span className="amount">{price}</span>
                  <span className="period">/ міс</span>
                </div>
              </div>

              <div className="plan-features">
                {(PLAN_FEATURES[plan.code] || []).map(f => (
                  <div key={f} className="feature-item">
                    <span className="check">✦</span> {f}
                  </div>
                ))}
              </div>

              <div className="plan-footer mt-auto">
                <button 
                  className={`btn-luxury ${isCurrent ? 'btn-current' : isPro ? 'btn-featured' : 'btn-standard'}`}
                  onClick={() => handleSubscribe(plan.code)}
                  disabled={subscribing !== null || isCurrent}
                >
                  {subscribing === plan.code ? (
                    <span className="flex items-center gap-2"><div className="spinner-sm"></div> Обробка...</span>
                  ) : isCurrent ? "Ваш поточний тариф" : "Обрати цей план"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="subscription-status-luxury card-elevated mt-16 p-8">
        <div className="flex justify-between items-center flex-wrap gap-6">
          <div className="status-info">
            <span className="badge-luxury mb-2">Деталі підписки</span>
            <div className="current-plan-display flex items-center gap-3">
              <span className="status-indicator active"></span>
              <h4>{PLAN_LABELS[currentPlan]} — {subscription?.status === 'active' ? 'Активний' : 'Потребує уваги'}</h4>
            </div>
          </div>
          
          {subscription?.usage && (
            <div className="usage-stats flex gap-8">
              <div className="stat-box">
                <label>Використання лімітів</label>
                <div className="stat-value">
                  {subscription.usage.docs_used} <span>/ {subscription.usage.docs_limit || "∞"}</span>
                </div>
                <div className="progress-bar">
                   <div className="progress-fill" style={{ width: `${Math.min(100, (subscription.usage.docs_used / (subscription.usage.docs_limit || 1)) * 100)}%` }}></div>
                </div>
              </div>
              <div className="stat-box">
                <label>Наступне списання</label>
                <div className="stat-value date">
                  {subscription.usage.current_period_end ? new Date(subscription.usage.current_period_end).toLocaleDateString("uk-UA") : "—"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {currentPlan === "PRO_PLUS" && (
        <div className="branding-section-luxury mt-16 animate-slide-up">
          <div className="section-header mb-8">
             <h2 className="luxury-title-sm">Брендування White-labeling</h2>
             <p className="text-muted">Персоналізуйте звіти та документи власним логотипом компанії.</p>
          </div>
          <div className="card-elevated p-8">
            <LogoUpload 
              initialLogoUrl={(subscription as any)?.logo_url} 
              onSuccess={(url) => setSubscription(s => s ? { ...s, logo_url: url } : s)}
            />
          </div>
        </div>
      )}

      {liqpayForm && (
        <div className="liqpay-modal-luxury animate-bounce-in">
          <div className="card-elevated p-10 text-center border-gold">
            <div className="payment-icon">💳</div>
            <h2 className="text-2xl font-black mb-4">Фіналізація транзакції</h2>
            <p className="text-secondary mb-8 max-w-md mx-auto">
              Ви обрали професійний рівень інструментів. Натисніть кнопку нижче для переходу на захищений шлюз **LiqPay**.
            </p>
            <form method="POST" action={liqpayForm.url} target="_blank">
              <input type="hidden" name="data" value={liqpayForm.data} />
              <input type="hidden" name="signature" value={liqpayForm.sig} />
              <button type="submit" className="btn-luxury btn-featured btn-lg w-full">
                 ОПЛАТИТИ ЧЕРЕЗ LIQPAY
              </button>
            </form>
          </div>
        </div>
      )}

      <style jsx>{`
        .billing-luxury-container { padding-bottom: 80px; }
        .section-header-centered { text-align: center; margin-bottom: 60px; }
        .luxury-title { font-size: 48px; font-weight: 950; letter-spacing: -0.04em; margin-bottom: 12px; background: linear-gradient(to right, #fff, var(--gold-400)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .luxury-subtitle { font-size: 18px; color: var(--text-secondary); max-width: 700px; margin: 0 auto; }
        .luxury-title-sm { font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 8px; }

        .billing-toggle {
          display: inline-flex;
          background: rgba(255, 255, 255, 0.05);
          padding: 6px;
          border-radius: 100px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .billing-toggle button {
          padding: 10px 24px;
          border-radius: 100px;
          border: none;
          background: transparent;
          color: var(--text-secondary);
          font-weight: 700;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.3s;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .billing-toggle button.active { background: var(--gold-500); color: var(--navy-950); box-shadow: 0 4px 15px rgba(212, 168, 67, 0.4); }
        .save-badge { font-size: 10px; background: rgba(0, 0, 0, 0.2); padding: 2px 6px; border-radius: 6px; font-weight: 800; }

        .pricing-grid-luxury {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
          gap: 32px;
        }

        .plan-card-luxury {
          background: rgba(11, 22, 40, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 32px;
          padding: 48px;
          position: relative;
          transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .plan-card-luxury:hover { transform: translateY(-12px); border-color: rgba(255, 255, 255, 0.2); box-shadow: 0 40px 80px rgba(0,0,0,0.6); }
        .plan-card-luxury.featured { border-color: var(--gold-500); background: linear-gradient(180deg, rgba(212, 168, 67, 0.05), rgba(11, 22, 40, 0.6)); }
        .plan-card-luxury.active { border-color: var(--success); }

        .featured-ribbon {
          position: absolute; top: 20px; right: -35px;
          background: var(--gold-500); color: #000;
          font-size: 10px; font-weight: 900;
          padding: 8px 40px; transform: rotate(45deg);
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          letter-spacing: 1px;
        }

        .plan-icon { font-size: 40px; margin-bottom: 24px; }
        .plan-header h3 { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 20px; }
        .plan-price { margin-bottom: 40px; display: flex; align-items: baseline; }
        .currency { font-size: 20px; font-weight: 600; color: var(--text-muted); margin-right: 4px; }
        .amount { font-size: 56px; font-weight: 900; color: #fff; line-height: 1; }
        .period { font-size: 16px; color: var(--text-muted); margin-left: 8px; }

        .plan-features { margin-bottom: 48px; }
        .feature-item { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; font-size: 15px; color: var(--text-secondary); }
        .feature-item .check { color: var(--gold-400); font-weight: bold; }

        .btn-luxury {
          width: 100%; padding: 18px; border-radius: 16px;
          font-weight: 800; font-size: 14px; text-transform: uppercase;
          letter-spacing: 1px; cursor: pointer; transition: all 0.3s;
          border: none;
        }
        .btn-standard { background: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid rgba(255, 255, 255, 0.1); }
        .btn-standard:hover { background: rgba(255,255,255,0.1); border-color: #fff; }
        .btn-featured { background: linear-gradient(135deg, var(--gold-500), #f5d17e); color: #000; box-shadow: 0 10px 25px rgba(212, 168, 67, 0.3); }
        .btn-featured:hover { transform: scale(1.03); box-shadow: 0 15px 35px rgba(212, 168, 67, 0.5); }
        .btn-current { background: var(--success); color: #fff; cursor: default; }

        .progress-bar { height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; margin-top: 8px; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--gold-500); box-shadow: 0 0 10px var(--gold-500); border-radius: 3px; }

        .stat-box label { font-size: 11px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px; }
        .stat-value { font-size: 24px; font-weight: 800; color: #fff; }
        .stat-value span { color: var(--text-muted); font-size: 14px; }
        .stat-value.date { font-size: 20px; }

        .badge-luxury { display: inline-block; background: rgba(212, 168, 67, 0.1); color: var(--gold-400); padding: 4px 12px; border-radius: 100px; font-size: 10px; font-weight: 800; text-transform: uppercase; border: 1px solid rgba(212, 168, 67, 0.2); }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .status-indicator.active { background: var(--success); box-shadow: 0 0 10px var(--success); }

        .alert-premium { padding: 20px 32px; border-radius: 16px; margin-bottom: 32px; font-weight: 700; border: 1px solid transparent; }
        .alert-premium.success { background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); color: #10b981; }
        .alert-premium.danger { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #ef4444; }

        .payment-icon { font-size: 64px; margin-bottom: 24px; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.7; transform: scale(1.1); } 100% { opacity: 1; transform: scale(1); } }
        
        .border-gold { border: 2px solid var(--gold-500) !important; box-shadow: 0 0 50px rgba(212, 168, 67, 0.2) !important; }

        .spinner-sm { width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
