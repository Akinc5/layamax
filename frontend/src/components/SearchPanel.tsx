"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import type { PostData } from "@/lib/types";
import PostCard from "./PostCard";

export default function SearchPanel() {
  const [filters, setFilters] = useState({
    keyword: "",
    username: "",
    hashtag: "",
    topic: "",
    sentiment: "",
    importance: "",
    min_relevance: "",
  });
  const [results, setResults] = useState<PostData[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSearched(true);

    const params: Record<string, unknown> = {};
    if (filters.keyword) params.keyword = filters.keyword;
    if (filters.username) params.username = filters.username;
    if (filters.hashtag) params.hashtag = filters.hashtag;
    if (filters.topic) params.topic = filters.topic;
    if (filters.sentiment) params.sentiment = filters.sentiment;
    if (filters.importance) params.importance = filters.importance;
    if (filters.min_relevance) params.min_relevance = parseFloat(filters.min_relevance);
    params.limit = 30;

    try {
      const data = await api.search(params) as PostData[];
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const topics = [
    "", "AI", "Machine Learning", "Technology", "Startups",
    "Finance", "Politics", "Sports", "Science",
    "Cybersecurity", "Climate", "Gaming",
  ];

  return (
    <div className="space-y-4">
      <div className="lp-card">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Search & Filter</h3>
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Keyword
              </label>
              <input
                type="text"
                value={filters.keyword}
                onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
                placeholder="Search text…"
                className="lp-input text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Username
              </label>
              <input
                type="text"
                value={filters.username}
                onChange={(e) => setFilters({ ...filters, username: e.target.value })}
                placeholder="@username"
                className="lp-input text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Hashtag
              </label>
              <input
                type="text"
                value={filters.hashtag}
                onChange={(e) => setFilters({ ...filters, hashtag: e.target.value })}
                placeholder="#hashtag"
                className="lp-input text-xs"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Topic
              </label>
              <select
                value={filters.topic}
                onChange={(e) => setFilters({ ...filters, topic: e.target.value })}
                className="lp-input text-xs"
              >
                {topics.map((t) => (
                  <option key={t} value={t} className="bg-gray-900">
                    {t || "All Topics"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Sentiment
              </label>
              <select
                value={filters.sentiment}
                onChange={(e) => setFilters({ ...filters, sentiment: e.target.value })}
                className="lp-input text-xs"
              >
                <option value="" className="bg-gray-900">Any</option>
                <option value="positive" className="bg-gray-900">Positive</option>
                <option value="neutral" className="bg-gray-900">Neutral</option>
                <option value="negative" className="bg-gray-900">Negative</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Importance
              </label>
              <select
                value={filters.importance}
                onChange={(e) => setFilters({ ...filters, importance: e.target.value })}
                className="lp-input text-xs"
              >
                <option value="" className="bg-gray-900">Any</option>
                <option value="CRITICAL" className="bg-gray-900">Critical</option>
                <option value="HIGH" className="bg-gray-900">High</option>
                <option value="MEDIUM" className="bg-gray-900">Medium</option>
                <option value="LOW" className="bg-gray-900">Low</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 block">
                Min Relevance
              </label>
              <input
                type="number"
                value={filters.min_relevance}
                onChange={(e) => setFilters({ ...filters, min_relevance: e.target.value })}
                placeholder="0-100"
                min="0"
                max="100"
                className="lp-input text-xs"
              />
            </div>
            <div className="flex items-end">
              <button type="submit" disabled={loading} className="lp-btn-primary w-full">
                {loading ? "Searching…" : "Search"}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Results */}
      {searched && (
        <div>
          <div className="text-xs text-gray-500 mb-3">
            {results.length} results found
          </div>
          <div className="space-y-3">
            {results.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
            {results.length === 0 && (
              <div className="text-center py-12 text-gray-500 text-sm">
                No posts match your filters.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
