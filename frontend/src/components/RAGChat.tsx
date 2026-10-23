"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/api";
import type { RAGResponse, RAGCitation } from "@/lib/types";

export default function RAGChat() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [history, setHistory] = useState<Array<{ q: string; r: RAGResponse }>>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const q = question.trim();
    setQuestion("");
    setLoading(true);

    let accumulatedAnswer = "";
    let citations: RAGCitation[] = [];
    let queryTime = 0;

    setResponse({
      answer: "",
      citations: [],
      query_time_ms: 0,
    });

    try {
      for await (const chunk of api.queryRAGStream(q)) {
        if (chunk.type === "citations") {
          citations = (chunk.citations || []).map((c: any) => ({
            ...c,
            timestamp: new Date(c.timestamp),
          }));
          queryTime = chunk.retrieval_time_ms || 0;
          setResponse({
            answer: accumulatedAnswer,
            citations,
            query_time_ms: queryTime,
          });
        } else if (chunk.type === "token") {
          accumulatedAnswer += chunk.token;
          setResponse({
            answer: accumulatedAnswer,
            citations,
            query_time_ms: queryTime,
          });
        } else if (chunk.type === "done") {
          if (chunk.total_time_ms) queryTime = chunk.total_time_ms;
          const finalResult: RAGResponse = {
            answer: accumulatedAnswer,
            citations,
            query_time_ms: queryTime,
          };
          setResponse(finalResult);
          setHistory((prev) => [{ q, r: finalResult }, ...prev].slice(0, 10));
        }
      }
    } catch {
      setResponse({
        answer: "Failed to stream response from the live RAG model. Please check connection.",
        citations: [],
        query_time_ms: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "What happened in AI today?",
    "Why is OpenAI trending?",
    "What are the latest cybersecurity threats?",
    "Summarize recent technology news",
  ];

  return (
    <div className="lp-card">
      <div className="flex items-center gap-2 mb-4">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <h3 className="text-sm font-semibold text-gray-300">Ask LayaPulse</h3>
        <span className="text-[10px] text-gray-500 ml-auto uppercase tracking-wider">RAG-Powered</span>
      </div>

      {/* Suggested questions */}
      {!response && history.length === 0 && (
        <div className="mb-4">
          <p className="text-[11px] text-gray-500 mb-2">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((sq) => (
              <button
                key={sq}
                onClick={() => setQuestion(sq)}
                className="text-[11px] px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-400
                           border border-indigo-500/15 hover:bg-indigo-500/20 transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Answer display */}
      {response && (
        <div className="mb-4 animate-fade-in">
          <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.06]">
            <div className="prose prose-sm prose-invert max-w-none">
              {response.answer.split("\n").map((line, i) => {
                if (line.startsWith("**") && line.endsWith("**")) {
                  return (
                    <h4 key={i} className="text-sm font-semibold text-gray-200 mt-3 mb-1">
                      {line.replace(/\*\*/g, "")}
                    </h4>
                  );
                }
                if (line.startsWith("•") || line.startsWith("- ")) {
                  return (
                    <p key={i} className="text-xs text-gray-300 pl-3 py-0.5 border-l border-indigo-500/20">
                      {line}
                    </p>
                  );
                }
                if (line.startsWith("*") && line.endsWith("*")) {
                  return (
                    <p key={i} className="text-[11px] text-gray-500 italic mt-2">
                      {line.replace(/\*/g, "")}
                    </p>
                  );
                }
                return line ? (
                  <p key={i} className="text-xs text-gray-300 leading-relaxed">
                    {line}
                  </p>
                ) : <br key={i} />;
              })}
              {loading && (
                <span className="inline-block w-1.5 h-3.5 bg-indigo-400 ml-1 animate-pulse align-middle" />
              )}
            </div>

            {/* Query time */}
            <div className="mt-3 pt-2 border-t border-white/[0.04] text-[10px] text-gray-500">
              ⚡ {response.query_time_ms.toFixed(0)}ms · {response.citations.length} sources
            </div>
          </div>

          {/* Citations */}
          {response.citations.length > 0 && (
            <div className="mt-3">
              <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                Sources
              </p>
              <div className="space-y-1.5">
                {response.citations.slice(0, 5).map((cite: RAGCitation, i: number) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                  >
                    <span className="text-[10px] font-mono text-indigo-400 mt-0.5">
                      [{i + 1}]
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium text-gray-300">
                          @{cite.author_username}
                        </span>
                        <span className="text-[10px] text-gray-500">
                          {timeAgo(cite.timestamp)}
                        </span>
                        <span className="text-[10px] text-indigo-400 ml-auto">
                          {cite.relevance_score.toFixed(0)}% match
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-400 line-clamp-2 mt-0.5">
                        {cite.text}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about the live feed…"
          className="lp-input flex-1"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="lp-btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="animate-spin">⏳</span>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
          Ask
        </button>
      </form>
    </div>
  );
}
