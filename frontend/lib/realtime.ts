"use client";

import { useEffect, useMemo, useState } from "react";

import { getToken, getUserId } from "@/lib/auth";

export type RealtimeStatus = "idle" | "connecting" | "reconnecting" | "connected" | "disconnected" | "error";

export type RealtimeMessage = {
  event: string;
  payload: Record<string, unknown>;
  received_at: string;
};

type UseRealtimeNotificationsOptions = {
  enabled?: boolean;
  maxEvents?: number;
};

const DEFAULT_MAX_EVENTS = 12;

function resolveApiBase(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8000";
    }
  }

  if (typeof window === "undefined") {
    return "http://backend:8000";
  }
  return "https://backend-production-0e53.up.railway.app";
}

function toWebSocketBase(apiBase: string): string {
  return apiBase.replace(/^http:\/\//i, "ws://").replace(/^https:\/\//i, "wss://");
}

function buildWebSocketUrl(): string {
  const wsBase = toWebSocketBase(resolveApiBase());
  const params = new URLSearchParams();
  const token = getToken();
  const userId = getUserId();

  if (token) {
    params.set("token", token);
  } else if (userId) {
    params.set("demo_user", userId);
  }

  const query = params.toString();
  return `${wsBase}/api/notifications/ws${query ? `?${query}` : ""}`;
}

function normalizeMessage(raw: unknown): RealtimeMessage | null {
  if (!raw || typeof raw !== "object") return null;
  const input = raw as Record<string, unknown>;
  const event = typeof input.event === "string" ? input.event : "";
  if (!event) return null;
  const payload = input.payload && typeof input.payload === "object" ? (input.payload as Record<string, unknown>) : {};
  return {
    event,
    payload,
    received_at: new Date().toISOString(),
  };
}

export function useRealtimeNotifications(options: UseRealtimeNotificationsOptions = {}) {
  const enabled = options.enabled ?? true;
  const maxEvents = options.maxEvents ?? DEFAULT_MAX_EVENTS;

  const [status, setStatus] = useState<RealtimeStatus>("idle");
  const [events, setEvents] = useState<RealtimeMessage[]>([]);

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || process.env.NODE_ENV === "test") {
      return;
    }

    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let attempt = 0;

    const clearTimers = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
    };

    const connect = () => {
      if (!active) return;
      setStatus(attempt > 0 ? "reconnecting" : "connecting");

      try {
        socket = new WebSocket(buildWebSocketUrl());
      } catch {
        setStatus("error");
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        if (!active) return;
        attempt = 0;
        setStatus("connected");
        clearTimers();
        pingTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, 25_000);
      };

      socket.onmessage = (messageEvent) => {
        if (!active) return;
        try {
          const parsed = JSON.parse(String(messageEvent.data));
          const normalized = normalizeMessage(parsed);
          if (!normalized) return;
          setEvents((previous) => [normalized, ...previous].slice(0, maxEvents));
        } catch {
          // Ignore malformed websocket payloads.
        }
      };

      socket.onerror = () => {
        if (!active) return;
        setStatus("error");
      };

      socket.onclose = () => {
        if (!active) return;
        setStatus("disconnected");
        clearTimers();
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (!active) return;
      attempt += 1;
      const delayMs = Math.min(15000, 1000 * 2 ** Math.min(attempt, 4));
      reconnectTimer = setTimeout(() => {
        connect();
      }, delayMs);
    };

    connect();

    return () => {
      active = false;
      clearTimers();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, "component_unmount");
      } else if (socket) {
        socket.close();
      }
      socket = null;
    };
  }, [enabled, maxEvents]);

  const lastEvent = useMemo(() => events[0] ?? null, [events]);

  return {
    status,
    events,
    lastEvent,
  };
}
