/* ═══════════════════════════════════════════════════════════════════
   API client + WebSocket hook for LayaPulse
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// ── REST helpers ────────────────────────────────────────────────
async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Stats
  getStats: () => fetchJSON("/api/stats"),

  // Posts
  getPosts: (limit = 50) => fetchJSON(`/api/posts?limit=${limit}`),
  getPost: (id: number) => fetchJSON(`/api/posts/${id}`),

  // Topics
  getTopicPosts: (topic: string, limit = 50) =>
    fetchJSON(`/api/topics/${encodeURIComponent(topic)}/posts?limit=${limit}`),
  getCategories: () => fetchJSON<string[]>("/api/categories"),
  updateCategories: (cats: string[]) =>
    fetchJSON("/api/categories", { method: "PUT", body: JSON.stringify(cats) }),

  // Analytics
  getAnalytics: (hours = 24) => fetchJSON(`/api/analytics?hours=${hours}`),

  // Events
  getEvents: (status = "active", limit = 20) =>
    fetchJSON(`/api/events?status=${status}&limit=${limit}`),
  getEventPosts: (eventId: number) => fetchJSON(`/api/events/${eventId}/posts`),

  // RAG
  queryRAG: (question: string, timeRangeHours?: number) =>
    fetchJSON("/api/rag", {
      method: "POST",
      body: JSON.stringify({ question, time_range_hours: timeRangeHours }),
    }),

  queryRAGStream: async function* (question: string, timeRangeHours?: number) {
    const res = await fetch(`${API_BASE}/api/rag/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, time_range_hours: timeRangeHours }),
    });
    if (!res.ok) throw new Error(`Stream error: ${res.status}`);
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            // ignore malformed chunks
          }
        }
      }
    }
  },

  // Stream Management
  getStreamStatus: () => fetchJSON("/api/stream/status"),
  ingestTweet: (text: string, author = "user") =>
    fetchJSON(`/api/stream/ingest?text=${encodeURIComponent(text)}&author=${encodeURIComponent(author)}`, {
      method: "POST",
    }),

  // Search
  search: (params: Record<string, unknown>) =>
    fetchJSON("/api/search", { method: "POST", body: JSON.stringify(params) }),

  // Alerts
  listAlerts: () => fetchJSON("/api/alerts"),
  createAlert: (name: string, conditions: Record<string, unknown>) =>
    fetchJSON("/api/alerts", {
      method: "POST",
      body: JSON.stringify({ name, conditions }),
    }),
  deleteAlert: (id: number) =>
    fetchJSON(`/api/alerts/${id}`, { method: "DELETE" }),
  getNotifications: (limit = 50) =>
    fetchJSON(`/api/alerts/notifications?limit=${limit}`),

  // Health
  health: () => fetchJSON("/api/health"),
};

import type { WSMessage } from "./types";

export function createWebSocket(
  onMessage: (msg: WSMessage) => void,
  onOpen?: () => void,
  onClose?: () => void,
): WebSocket | null {
  if (typeof window === "undefined") return null;

  const ws = new WebSocket(`${WS_BASE}/ws`);

  ws.onopen = () => {
    console.log("[LayaPulse] WebSocket connected");
    onOpen?.();
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      onMessage(msg);
    } catch (e) {
      console.error("[LayaPulse] Failed to parse WS message", e);
    }
  };

  ws.onclose = () => {
    console.log("[LayaPulse] WebSocket disconnected");
    onClose?.();
  };

  ws.onerror = (err) => {
    console.error("[LayaPulse] WebSocket error", err);
  };

  return ws;
}

// ── Formatting helpers ──────────────────────────────────────────
export function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}
