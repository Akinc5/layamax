"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createWebSocket } from "@/lib/api";
import type { DashboardStats, PostData, WSMessage } from "@/lib/types";

const MAX_POSTS = 100;

export function useLayaPulse() {
  const [posts, setPosts] = useState<PostData[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    posts_received: 0,
    posts_analyzed: 0,
    posts_indexed: 0,
    alerts_generated: 0,
    posts_per_minute: 0,
    avg_latency_ms: 0,
    is_live: false,
    stream_mode: "mock",
  });
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [alerts, setAlerts] = useState<Array<Record<string, unknown>>>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "new_post":
        setPosts((prev) => [msg.data as PostData, ...prev].slice(0, MAX_POSTS));
        break;
      case "stats_update":
        setStats(msg.data as DashboardStats);
        break;
      case "new_event":
        setEvents((prev) => [msg.data as Record<string, unknown>, ...prev].slice(0, 50));
        break;
      case "new_alert":
        setAlerts((prev) => [msg.data as Record<string, unknown>, ...prev].slice(0, 50));
        break;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    wsRef.current = createWebSocket(
      handleMessage,
      () => setConnected(true),
      () => {
        setConnected(false);
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(() => connect(), 3000);
      },
    );
  }, [handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { posts, stats, events, alerts, connected };
}
