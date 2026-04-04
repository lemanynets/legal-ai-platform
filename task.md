# Legal AI Platform → Production Roadmap

## ФАЗА 1: Design System & Landing Page [DONE]
- [x] Встановити Google Fonts (Inter) + оновити globals.css до преміум дизайн-системи
- [x] Замінити homepage (`app/page.tsx`) на красивий landing page з CTA та планами
- [x] Оновити sidebar/nav layout — бічна панель замість горизонтальної навігації
- [x] Додати спільний AuthGuard компонент (перевірка токена, редирект на login)
- [x] Створити `/login` сторінку (готовність до підключення Supabase)

## ФАЗА 2: Proper Supabase Auth Integration [DONE]
- [x] Встановити `@supabase/supabase-js`
- [x] Оновити `lib/auth.ts` для роботи з реальним Supabase client
- [x] Кастомна `onAuthStateChange` логіка з підтримкою dev-режиму
- [x] Забезпечити автоматичне оновлення токена (refresh session)

## ФАЗА 3: UI Redesign (Всі сторінки) [DONE]
- [x] `/dashboard` — Dashboard головна (stats, shortcuts)
- [x] `/dashboard/billing` — Преміум картки тарифів із реальним LiqPay redirect
- [x] `/dashboard/generate` — Зручний UI для генерації документів
- [x] `/dashboard/documents` — Красива таблиця з фільтрами
- [x] `/dashboard/full-lawyer` — Drag & drop upload + progress steps
- [x] `/dashboard/calculators` — Інтерактивні форми калькуляторів
- [x] `/dashboard/case-law` — Пошук + преміум картки прецедентів (укр UI)
- [x] Решта сторінок (analyze, deadlines, reports, monitoring, strategy, audit, team)

## ФАЗА 4: Backend Production Security
- [x] Fix `auth.py` to accept local `dev-token-` without Supabase configuration
- [x] Налаштувати production `.env` template
- [x] Перевірити що `ALLOW_DEV_AUTH=false` блокує доступ без реального JWT
- [x] Додати rate limiting (slowapi) — 100/minute global
- [x] Додати Production CORS whitelist — через `settings.allowed_origins`

## ФАЗА 5: File Storage
- [x] Додати Supabase Storage upload/download в `document_storage.py` (з fallback на локальне)
- [x] Реалізувати генерацію Signed URLs для прямого скачування з Cloud
- [x] Налаштувати роути для стрімінгу/видачі файлів

## ФАЗА 6: Deploy & Конфігурація [DONE]
- [x] Оновити `docker-compose.yml` для production (security, volumes)
- [x] Написати production `.env.production.example`
- [x] Створити `frontend/Dockerfile`
- [x] Оновити документацію в `walkthrough.md`

## ФАЗА 7: Verification [DONE]
- [x] Запустити backend + frontend локально через Docker Compose
- [x] Перевірити всі головні флоу через browser
- [x] Вирішити проблему "Unexpected token" у CSS (Nuke & Pave)
- [x] Перевірити що demo-auth повністю відключено при `ALLOW_DEV_AUTH=false`

**Платформа готова до продажу! ⚖️🚀**
