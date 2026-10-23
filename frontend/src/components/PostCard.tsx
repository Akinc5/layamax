"use client";

import React, { useState } from "react";
import type { PostData } from "@/lib/types";
import { CATEGORY_BADGE_CLASS } from "@/lib/types";
import { timeAgo, formatNumber } from "@/lib/api";

interface Props {
  post: PostData;
}

export default function PostCard({ post }: Props) {
  const [showExplain, setShowExplain] = useState(false);

  const categoryClass = CATEGORY_BADGE_CLASS[post.category || "Other"] || "badge-other";

  const sentimentColor =
    post.sentiment === "positive"
      ? "text-emerald-400"
      : post.sentiment === "negative"
        ? "text-red-400"
        : "text-gray-400";

  const importanceColor =
    post.importance === "CRITICAL"
      ? "text-red-400"
      : post.importance === "HIGH"
        ? "text-amber-400"
        : post.importance === "MEDIUM"
          ? "text-blue-400"
          : "text-gray-400";

  const importanceBg =
    post.importance === "CRITICAL"
      ? "bg-red-500/10 border-red-500/20"
      : post.importance === "HIGH"
        ? "bg-amber-500/10 border-amber-500/20"
        : "";

  return (
    <div
      className={`lp-card animate-slide-in-up ${importanceBg ? `border ${importanceBg}` : ""}`}
    >
      {/* Header row: avatar + username + time */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <img
            src={post.author_avatar}
            alt={post.author_name}
            className="w-10 h-10 rounded-full bg-gray-800"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">{post.author_name}</span>
              <span className="text-xs text-gray-500">@{post.author_username}</span>
            </div>
            <span className="text-[11px] text-gray-500">{timeAgo(post.timestamp)}</span>
          </div>
        </div>

        {/* Category badge */}
        {post.category && (
          <span className={`badge ${categoryClass}`}>{post.category}</span>
        )}
      </div>

      {/* Post text */}
      <p className="text-sm text-gray-200 leading-relaxed mb-3">{post.text}</p>

      {/* Hashtags */}
      {post.hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {post.hashtags.map((tag) => (
            <span
              key={tag}
              className="text-[11px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-md"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Entities */}
      {post.entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {post.entities.map((ent) => (
            <span
              key={ent.name}
              className="text-[11px] text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-md border border-cyan-500/10"
            >
              {ent.name}
            </span>
          ))}
        </div>
      )}

      {/* Metrics row */}
      <div className="flex items-center gap-4 pt-3 border-t border-white/[0.04]">
        {/* Sentiment */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase text-gray-500">Sentiment</span>
          <span className={`text-xs font-semibold capitalize ${sentimentColor}`}>
            {post.sentiment}
          </span>
        </div>

        {/* Relevance */}
        {post.relevance !== null && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase text-gray-500">Relevance</span>
            <span className="text-xs font-semibold text-indigo-400">
              {post.relevance.toFixed(0)}%
            </span>
          </div>
        )}

        {/* Importance */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] uppercase text-gray-500">Importance</span>
          <span className={`text-xs font-bold ${importanceColor}`}>
            {post.importance}
          </span>
        </div>

        {/* Engagement */}
        <div className="ml-auto flex items-center gap-3 text-gray-500">
          <span className="text-[11px]" title="Likes">♥ {formatNumber(post.likes)}</span>
          <span className="text-[11px]" title="Reposts">🔁 {formatNumber(post.reposts)}</span>
          <span className="text-[11px]" title="Views">👁 {formatNumber(post.views)}</span>
        </div>
      </div>

      {/* Explainability toggle */}
      {post.explanation && (
        <div className="mt-3">
          <button
            onClick={() => setShowExplain(!showExplain)}
            className="text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
            {showExplain ? "Hide" : "Why this classification?"}
          </button>
          {showExplain && (
            <div className="mt-2 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-gray-300 leading-relaxed animate-fade-in">
              <div className="font-semibold text-indigo-400 mb-1">Laya Decision Explanation</div>
              <p>{post.explanation}</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                <div><span className="text-gray-500">Category:</span> {post.category}</div>
                <div><span className="text-gray-500">Sentiment:</span> {post.sentiment} ({post.sentiment_score?.toFixed(2)})</div>
                <div><span className="text-gray-500">Relevance:</span> {post.relevance?.toFixed(1)}%</div>
                <div><span className="text-gray-500">Importance:</span> {post.importance} ({post.importance_score?.toFixed(1)})</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
