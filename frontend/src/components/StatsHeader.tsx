"use client";

import React from "react";
import type { DashboardStats } from "@/lib/types";

interface Props {
  stats: DashboardStats;
  connected: boolean;
}

export default function StatsHeader({ stats, connected }: Props) {
  const statItems = [
    { label: "Posts / min", value: stats.posts_per_minute.toFixed(1), color: "text-indigo-400" },
    { label: "Analyzed", value: stats.posts_analyzed.toLocaleString(), color: "text-emerald-400" },
    { label: "Indexed", value: stats.posts_indexed.toLocaleString(), color: "text-blue-400" },
    { label: "Alerts", value: stats.alerts_generated.toLocaleString(), color: "text-amber-400" },
    { label: "Latency", value: `${stats.avg_latency_ms.toFixed(0)}ms`, color: "text-purple-400" },
  ];

  return (
    <header className="border-b border-white/[0.06] bg-[#0a0d14]/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-[1920px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo + Live status */}
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight">
                  Laya<span className="text-indigo-400">Pulse</span>
                </h1>
                <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-gray-500">
                  Real-Time X Intelligence
                </p>
              </div>
            </div>

            {/* Live indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
              <div className={`w-2 h-2 rounded-full ${connected ? "live-dot" : "bg-red-500"}`} />
              <span className={`text-xs font-semibold uppercase tracking-wider ${connected ? "text-emerald-400" : "text-red-400"}`}>
                {connected ? "LIVE" : "OFFLINE"}
              </span>
              {connected && (
                <span className="text-[10px] text-gray-500 font-medium ml-1">
                  {stats.stream_mode === "mock" ? "MOCK" : "LIVE"} DATA
                </span>
              )}
            </div>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-1">
            {statItems.map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center px-4 py-1 rounded-lg hover:bg-white/[0.03] transition-colors"
              >
                <span className={`stat-value text-base ${item.color}`}>
                  {item.value}
                </span>
                <span className="stat-label text-[9px]">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}
