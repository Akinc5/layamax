/* ═══════════════════════════════════════════════════════════════════
   LayaPulse TypeScript Types
   ═══════════════════════════════════════════════════════════════════ */

// ── Post ────────────────────────────────────────────────────────
export interface EntityInfo {
  name: string;
  entity_type: string;
}

export interface PostData {
  id: number;
  external_id: string;
  author_name: string;
  author_username: string;
  author_avatar: string;
  text: string;
  timestamp: string;
  url: string;
  likes: number;
  reposts: number;
  replies: number;
  views: number;
  processing_timestamp: string | null;
  category: string | null;
  sentiment: string | null;
  sentiment_score: number | null;
  relevance: number | null;
  importance: string | null;
  importance_score: number | null;
  should_index: boolean | null;
  should_alert: boolean | null;
  is_significant_event: boolean | null;
  explanation: string | null;
  hashtags: string[];
  entities: EntityInfo[];
  mentioned_users: string[];
  extracted_urls: string[];
}

// ── Dashboard Stats ─────────────────────────────────────────────
export interface DashboardStats {
  posts_received: number;
  posts_analyzed: number;
  posts_indexed: number;
  alerts_generated: number;
  posts_per_minute: number;
  avg_latency_ms: number;
  is_live: boolean;
  stream_mode: string;
}

// ── Analytics ───────────────────────────────────────────────────
export interface SentimentBreakdown {
  positive: number;
  neutral: number;
  negative: number;
}

export interface TopicCount {
  topic: string;
  count: number;
}

export interface ActivityPoint {
  timestamp: string;
  count: number;
}

export interface ImportanceBreakdown {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface TrendingEntity {
  name: string;
  count: number;
  velocity: number;
  trend: "rising" | "falling" | "stable";
}

export interface AnalyticsData {
  sentiment: SentimentBreakdown;
  topics: TopicCount[];
  activity: ActivityPoint[];
  importance: ImportanceBreakdown;
  trending_entities: TrendingEntity[];
}

// ── Events ──────────────────────────────────────────────────────
export interface EventData {
  id: number;
  title: string;
  description: string | null;
  category: string | null;
  severity: string;
  first_detected: string;
  last_updated: string | null;
  post_count: number;
  status: string;
  related_entities: string[] | null;
}

// ── RAG ─────────────────────────────────────────────────────────
export interface RAGCitation {
  post_id: number;
  author_username: string;
  text: string;
  timestamp: string;
  relevance_score: number;
}

export interface RAGResponse {
  answer: string;
  citations: RAGCitation[];
  query_time_ms: number;
}

// ── Alerts ──────────────────────────────────────────────────────
export interface AlertData {
  id: number;
  name: string;
  conditions: Record<string, unknown>;
  active: boolean;
  created_at: string;
}

export interface AlertNotification {
  id: number;
  alert_id: number;
  post_id: number;
  message: string;
  read: boolean;
  created_at: string;
}

// ── WebSocket ───────────────────────────────────────────────────
export interface WSMessage {
  type: "new_post" | "stats_update" | "new_event" | "new_alert";
  data: unknown;
}

// ── Category colours ────────────────────────────────────────────
export const CATEGORY_COLORS: Record<string, string> = {
  AI: "#6366f1",
  "Machine Learning": "#a855f7",
  Technology: "#3b82f6",
  Startups: "#10b981",
  Finance: "#f59e0b",
  Politics: "#f43f5e",
  Sports: "#f97316",
  Science: "#06b6d4",
  Cybersecurity: "#ef4444",
  Climate: "#14b8a6",
  Gaming: "#d946ef",
  Other: "#6b7280",
};

export const CATEGORY_BADGE_CLASS: Record<string, string> = {
  AI: "badge-ai",
  "Machine Learning": "badge-ml",
  Technology: "badge-tech",
  Startups: "badge-startups",
  Finance: "badge-finance",
  Politics: "badge-politics",
  Sports: "badge-sports",
  Science: "badge-science",
  Cybersecurity: "badge-cybersecurity",
  Climate: "badge-climate",
  Gaming: "badge-gaming",
  Other: "badge-other",
};
