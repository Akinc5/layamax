"use client";

import React, { useState } from "react";
import { useLayaPulse } from "@/hooks/useLayaPulse";
import StatsHeader from "@/components/StatsHeader";
import PostCard from "@/components/PostCard";
import AnalyticsPanel from "@/components/AnalyticsPanel";
import TrendingPanel from "@/components/TrendingPanel";
import EventsPanel from "@/components/EventsPanel";
import RAGChat from "@/components/RAGChat";
import SearchPanel from "@/components/SearchPanel";
import AlertsPanel from "@/components/AlertsPanel";

type Tab = "feed" | "analytics" | "search" | "alerts";

export default function Dashboard() {
  const { posts, stats, connected } = useLayaPulse();
  const [activeTab, setActiveTab] = useState<Tab>("feed");

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: "feed",
      label: "Live Feed",
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16" />
          <circle cx="5" cy="19" r="1" />
        </svg>
      ),
    },
    {
      id: "analytics",
      label: "Analytics",
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 20V10M12 20V4M6 20v-6" />
        </svg>
      ),
    },
    {
      id: "search",
      label: "Search",
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      ),
    },
    {
      id: "alerts",
      label: "Alerts",
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <StatsHeader stats={stats} connected={connected} />

      {/* Tab navigation */}
      <div className="border-b border-white/[0.06] bg-[#080b12]/50 backdrop-blur-sm sticky top-[73px] z-40">
        <div className="max-w-[1920px] mx-auto px-6">
          <nav className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-all ${
                  activeTab === tab.id
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-700"
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.id === "alerts" && stats.alerts_generated > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 text-[10px]">
                    {stats.alerts_generated}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 max-w-[1920px] mx-auto px-6 py-6 w-full">
        {activeTab === "feed" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left column: Live feed */}
            <div className="lg:col-span-7 xl:col-span-7 space-y-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="live-dot" />
                  <h2 className="text-sm font-semibold text-gray-300">Live Feed</h2>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {posts.length} posts
                  </span>
                </div>
              </div>

              {posts.length === 0 ? (
                <div className="lp-card text-center py-16">
                  <div className="text-4xl mb-4">⚡</div>
                  <p className="text-gray-400 text-sm">
                    Waiting for incoming posts…
                  </p>
                  <p className="text-gray-500 text-xs mt-1">
                    Posts will appear here in real-time
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {posts.map((post) => (
                    <PostCard key={post.id} post={post} />
                  ))}
                </div>
              )}
            </div>

            {/* Right column: Events + Trending + RAG */}
            <div className="lg:col-span-5 xl:col-span-5 space-y-4">
              <RAGChat />
              <EventsPanel />
              <TrendingPanel />
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="space-y-6">
            <AnalyticsPanel />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TrendingPanel />
              <EventsPanel />
            </div>
          </div>
        )}

        {activeTab === "search" && <SearchPanel />}

        {activeTab === "alerts" && <AlertsPanel />}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.04] py-4 px-6">
        <div className="max-w-[1920px] mx-auto flex items-center justify-between text-[10px] text-gray-600">
          <span>LayaPulse v1.0 · Powered by Laya Decision Engine</span>
          <span>
            &quot;Understand the live conversation.&quot;
          </span>
        </div>
      </footer>
    </div>
  );
}
