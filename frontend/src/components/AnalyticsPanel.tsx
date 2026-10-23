"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { api } from "@/lib/api";
import type { AnalyticsData } from "@/lib/types";
import { CATEGORY_COLORS } from "@/lib/types";

const SENTIMENT_COLORS = ["#10b981", "#6b7280", "#ef4444"];
const IMPORTANCE_COLORS = ["#6b7280", "#3b82f6", "#f59e0b", "#ef4444"];

export default function AnalyticsPanel() {
  const [data, setData] = useState<AnalyticsData | null>(null);

  const fetchAnalytics = useCallback(async () => {
    try {
      const result = await api.getAnalytics(6) as AnalyticsData;
      setData(result);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  if (!data) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="lp-card h-56 shimmer" />
        ))}
      </div>
    );
  }

  // Sentiment pie data
  const sentimentData = [
    { name: "Positive", value: data.sentiment.positive },
    { name: "Neutral", value: data.sentiment.neutral },
    { name: "Negative", value: data.sentiment.negative },
  ].filter((d) => d.value > 0);

  // Importance data
  const importanceData = [
    { name: "Low", value: data.importance.low },
    { name: "Medium", value: data.importance.medium },
    { name: "High", value: data.importance.high },
    { name: "Critical", value: data.importance.critical },
  ].filter((d) => d.value > 0);

  // Topics bar data (top 8)
  const topicsData = data.topics.slice(0, 8).map((t) => ({
    name: t.topic.length > 12 ? t.topic.slice(0, 12) + "…" : t.topic,
    fullName: t.topic,
    count: t.count,
    fill: CATEGORY_COLORS[t.topic] || "#6b7280",
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ── Sentiment ──────────────────────────────────── */}
      <div className="lp-card">
        <h3 className="text-sm font-semibold mb-4 text-gray-300">Sentiment Distribution</h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={sentimentData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={75}
                dataKey="value"
                stroke="none"
              >
                {sentimentData.map((_, i) => (
                  <Cell key={i} fill={SENTIMENT_COLORS[i]} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(value) => (
                  <span className="text-xs text-gray-400">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Topics ─────────────────────────────────────── */}
      <div className="lp-card">
        <h3 className="text-sm font-semibold mb-4 text-gray-300">Top Topics</h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topicsData} layout="vertical" margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis
                dataKey="name"
                type="category"
                width={90}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
              />
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(value: any, _: any, props: any) => [value ?? 0, props?.payload?.fullName ?? ""]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {topicsData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Activity ───────────────────────────────────── */}
      <div className="lp-card">
        <h3 className="text-sm font-semibold mb-4 text-gray-300">Activity Timeline</h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.activity.slice(-20)}>
              <defs>
                <linearGradient id="activityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#6366f1"
                fill="url(#activityGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Importance ─────────────────────────────────── */}
      <div className="lp-card">
        <h3 className="text-sm font-semibold mb-4 text-gray-300">Importance Levels</h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={importanceData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={75}
                dataKey="value"
                stroke="none"
              >
                {importanceData.map((_, i) => (
                  <Cell key={i} fill={IMPORTANCE_COLORS[i]} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(value) => (
                  <span className="text-xs text-gray-400">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
