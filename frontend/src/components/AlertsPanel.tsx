"use client";

import React, { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/api";
import type { AlertData, AlertNotification } from "@/lib/types";

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [notifications, setNotifications] = useState<AlertNotification[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newAlert, setNewAlert] = useState({ name: "", topic: "", min_relevance: "", importance: "", keyword: "" });

  const fetchAlerts = useCallback(async () => {
    try {
      const [alertList, notifList] = await Promise.all([
        api.listAlerts() as Promise<AlertData[]>,
        api.getNotifications(20) as Promise<AlertNotification[]>,
      ]);
      setAlerts(alertList);
      setNotifications(notifList);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const conditions: Record<string, unknown> = {};
    if (newAlert.topic) conditions.topic = newAlert.topic;
    if (newAlert.min_relevance) conditions.min_relevance = parseFloat(newAlert.min_relevance);
    if (newAlert.importance) conditions.importance = newAlert.importance;
    if (newAlert.keyword) conditions.keyword = newAlert.keyword;

    if (Object.keys(conditions).length === 0 || !newAlert.name) return;

    try {
      await api.createAlert(newAlert.name, conditions);
      setNewAlert({ name: "", topic: "", min_relevance: "", importance: "", keyword: "" });
      setShowCreate(false);
      fetchAlerts();
    } catch { /* silent */ }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteAlert(id);
      fetchAlerts();
    } catch { /* silent */ }
  };

  return (
    <div className="space-y-4">
      {/* Notifications */}
      <div className="lp-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <h3 className="text-sm font-semibold text-gray-300">Alert Notifications</h3>
          </div>
          <span className="text-[10px] text-gray-500">{notifications.length} recent</span>
        </div>

        {notifications.length === 0 ? (
          <p className="text-xs text-gray-500 text-center py-6">
            No alerts triggered yet.
          </p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className={`p-3 rounded-lg border text-xs ${
                  notif.read
                    ? "border-white/[0.04] bg-white/[0.01] text-gray-400"
                    : "border-amber-500/20 bg-amber-500/5 text-gray-200"
                }`}
              >
                <p className="line-clamp-2">{notif.message}</p>
                <span className="text-[10px] text-gray-500 mt-1 block">
                  {timeAgo(notif.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Alerts */}
      <div className="lp-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300">Active Alerts</h3>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="lp-btn-ghost text-xs flex items-center gap-1"
          >
            <span>+</span> New Alert
          </button>
        </div>

        {showCreate && (
          <form onSubmit={handleCreate} className="mb-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] space-y-2 animate-fade-in">
            <input
              type="text"
              value={newAlert.name}
              onChange={(e) => setNewAlert({ ...newAlert, name: e.target.value })}
              placeholder="Alert name"
              className="lp-input text-xs"
              required
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                value={newAlert.topic}
                onChange={(e) => setNewAlert({ ...newAlert, topic: e.target.value })}
                className="lp-input text-xs"
              >
                <option value="" className="bg-gray-900">Any Topic</option>
                {["AI", "Machine Learning", "Technology", "Startups", "Finance", "Cybersecurity", "Science", "Climate"].map((t) => (
                  <option key={t} value={t} className="bg-gray-900">{t}</option>
                ))}
              </select>
              <select
                value={newAlert.importance}
                onChange={(e) => setNewAlert({ ...newAlert, importance: e.target.value })}
                className="lp-input text-xs"
              >
                <option value="" className="bg-gray-900">Any Importance</option>
                <option value="HIGH" className="bg-gray-900">HIGH+</option>
                <option value="CRITICAL" className="bg-gray-900">CRITICAL</option>
              </select>
              <input
                type="text"
                value={newAlert.keyword}
                onChange={(e) => setNewAlert({ ...newAlert, keyword: e.target.value })}
                placeholder="Keyword"
                className="lp-input text-xs"
              />
              <input
                type="number"
                value={newAlert.min_relevance}
                onChange={(e) => setNewAlert({ ...newAlert, min_relevance: e.target.value })}
                placeholder="Min relevance (0-100)"
                className="lp-input text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="lp-btn-primary text-xs flex-1">
                Create Alert
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="lp-btn-ghost text-xs"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {alerts.length === 0 && !showCreate ? (
          <p className="text-xs text-gray-500 text-center py-6">
            No alerts configured. Create one to get notified.
          </p>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
              >
                <div>
                  <div className="text-sm font-medium text-gray-300">{alert.name}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {Object.entries(alert.conditions)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ")}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(alert.id)}
                  className="text-gray-500 hover:text-red-400 transition-colors text-xs"
                  title="Delete alert"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
