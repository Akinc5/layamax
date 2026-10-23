"use client";

import React, { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/api";
import type { EventData, PostData } from "@/lib/types";

export default function EventsPanel() {
  const [events, setEvents] = useState<EventData[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<number | null>(null);
  const [eventPosts, setEventPosts] = useState<PostData[]>([]);

  const fetchEvents = useCallback(async () => {
    try {
      const result = await api.getEvents("active", 10) as EventData[];
      setEvents(result);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 10000);
    return () => clearInterval(interval);
  }, [fetchEvents]);

  const handleEventClick = async (eventId: number) => {
    if (selectedEvent === eventId) {
      setSelectedEvent(null);
      setEventPosts([]);
      return;
    }
    setSelectedEvent(eventId);
    try {
      const posts = await api.getEventPosts(eventId) as PostData[];
      setEventPosts(posts);
    } catch {
      setEventPosts([]);
    }
  };

  const severityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return "border-red-500/30 bg-red-500/5";
      case "HIGH": return "border-amber-500/30 bg-amber-500/5";
      default: return "border-white/[0.06]";
    }
  };

  const severityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return "bg-red-500/15 text-red-400";
      case "HIGH": return "bg-amber-500/15 text-amber-400";
      case "MEDIUM": return "bg-blue-500/15 text-blue-400";
      default: return "bg-gray-500/15 text-gray-400";
    }
  };

  return (
    <div className="lp-card">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        <h3 className="text-sm font-semibold text-gray-300">Important Events</h3>
        <span className="ml-auto text-[10px] text-gray-500 uppercase tracking-wider">
          {events.length} active
        </span>
      </div>

      {events.length === 0 ? (
        <p className="text-xs text-gray-500 text-center py-8">
          No events detected yet. Monitoring…
        </p>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <div key={event.id}>
              <button
                onClick={() => handleEventClick(event.id)}
                className={`w-full text-left p-3 rounded-lg border transition-all hover:bg-white/[0.02] ${
                  severityColor(event.severity)
                } ${selectedEvent === event.id ? "ring-1 ring-indigo-500/30" : ""}`}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`badge text-[10px] ${severityBadge(event.severity)}`}>
                      {event.severity === "CRITICAL" ? "⚡ BREAKING" : event.severity}
                    </span>
                    {event.category && (
                      <span className="text-[10px] text-gray-500">{event.category}</span>
                    )}
                  </div>
                  <span className="text-[10px] text-gray-500">
                    {timeAgo(event.first_detected)}
                  </span>
                </div>

                <p className="text-sm font-medium text-gray-200 mb-2 line-clamp-2">
                  {event.title}
                </p>

                <div className="flex items-center gap-3 text-[11px] text-gray-500">
                  <span>📄 {event.post_count} sources</span>
                  {event.related_entities && event.related_entities.length > 0 && (
                    <span className="truncate">
                      🏷️ {event.related_entities.slice(0, 3).join(", ")}
                    </span>
                  )}
                </div>
              </button>

              {/* Expanded: supporting posts */}
              {selectedEvent === event.id && eventPosts.length > 0 && (
                <div className="ml-4 mt-2 space-y-2 animate-fade-in">
                  <div className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                    Supporting Posts
                  </div>
                  {eventPosts.slice(0, 5).map((post) => (
                    <div
                      key={post.id}
                      className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <img
                          src={post.author_avatar}
                          alt=""
                          className="w-5 h-5 rounded-full"
                        />
                        <span className="text-xs font-medium">@{post.author_username}</span>
                        <span className="text-[10px] text-gray-500 ml-auto">
                          {timeAgo(post.timestamp)}
                        </span>
                      </div>
                      <p className="text-xs text-gray-300 line-clamp-2">{post.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
