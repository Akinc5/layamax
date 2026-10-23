"use client";

import React, { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { TrendingEntity } from "@/lib/types";

export default function TrendingPanel() {
  const [entities, setEntities] = useState<TrendingEntity[]>([]);

  const fetchTrending = useCallback(async () => {
    try {
      const analytics = await api.getAnalytics(2) as { trending_entities: TrendingEntity[] };
      setEntities(analytics.trending_entities || []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchTrending();
    const interval = setInterval(fetchTrending, 15000);
    return () => clearInterval(interval);
  }, [fetchTrending]);

  const trendIcon = (trend: string) => {
    if (trend === "rising") return <span className="text-emerald-400">▲</span>;
    if (trend === "falling") return <span className="text-red-400">▼</span>;
    return <span className="text-gray-500">●</span>;
  };

  return (
    <div className="lp-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Trending Entities</h3>
        <span className="text-[10px] uppercase tracking-wider text-gray-500">Velocity</span>
      </div>

      {entities.length === 0 ? (
        <p className="text-xs text-gray-500 text-center py-8">
          Collecting data…
        </p>
      ) : (
        <div className="space-y-2">
          {entities.slice(0, 10).map((entity, i) => (
            <div
              key={entity.name}
              className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white/[0.03] transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-gray-500 w-4">
                  {(i + 1).toString().padStart(2, "0")}
                </span>
                <div className="flex items-center gap-2">
                  {trendIcon(entity.trend)}
                  <span className="text-sm font-medium">{entity.name}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400">{entity.count} mentions</span>
                <span
                  className={`text-[11px] font-mono px-2 py-0.5 rounded ${
                    entity.trend === "rising"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : entity.trend === "falling"
                        ? "bg-red-500/10 text-red-400"
                        : "bg-gray-500/10 text-gray-400"
                  }`}
                >
                  {entity.velocity > 0 ? "+" : ""}
                  {entity.velocity.toFixed(3)}/min
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
