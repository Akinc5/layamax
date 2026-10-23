"""
CLI entry point to execute the LayaPulse Evaluation Benchmark Suite.

Usage:
    python run_eval.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from eval_harness import EvaluationHarness


def print_banner(text: str) -> None:
    line = "=" * 74
    print(f"\n{line}")
    print(f"  {text}")
    print(f"{line}\n")


def print_metric_row(name: str, value: str, target: str = "", status: str = "PASS") -> None:
    status_color = "\033[1;32m[PASS]\033[0m" if status == "PASS" else "\033[1;33m[WARN]\033[0m"
    print(f"  {name:<36} : \033[1;37m{value:<12}\033[0m  {target:<14} {status_color}")


async def main() -> None:
    print_banner("LAYAPULSE EVALUATION HARNESS — BENCHMARK SUITE")
    print("  Initializing providers, benchmark dataset, and retrieval index...")

    harness = EvaluationHarness()
    results = await harness.run_full_suite()

    summary = results["summary"]
    cls_metrics = results["classification"]
    ir_metrics = results["retrieval"]
    perf_metrics = results["performance"]

    # ── 1. Classification Results ──
    print_banner("1. CLASSIFICATION PERFORMANCE")
    print("  Topic Classification (12 Classes):")
    print_metric_row("Topic Macro F1", f"{summary['topic_f1']:.4f}", "Target: > 0.85")
    print_metric_row("Topic Weighted F1", f"{cls_metrics['topic_classification']['weighted_f1']:.4f}", "Target: > 0.85")
    print_metric_row("Topic Overall Accuracy", f"{cls_metrics['topic_classification']['accuracy'] * 100:.1f}%", "Target: > 85%")
    print()
    print("  Sentiment Classification (Positive, Neutral, Negative):")
    print_metric_row("Sentiment Macro F1", f"{summary['sentiment_f1']:.4f}", "Target: > 0.85")
    print_metric_row("Sentiment Weighted F1", f"{cls_metrics['sentiment_classification']['weighted_f1']:.4f}", "Target: > 0.85")
    print_metric_row("Sentiment Accuracy", f"{cls_metrics['sentiment_classification']['accuracy'] * 100:.1f}%", "Target: > 85%")

    # ── 2. Information Retrieval / RAG ──
    print_banner("2. INFORMATION RETRIEVAL / RAG BENCHMARKS (25 Queries)")
    print_metric_row("Precision@1", f"{summary['precision_at_1']:.4f}", "Target: > 0.80")
    print_metric_row("Recall@1 (Hit@1)", f"{summary['recall_at_1'] * 100:.1f}%", "Target: > 80%")
    print_metric_row("Recall@3 (Hit@3)", f"{summary['recall_at_3'] * 100:.1f}%", "Target: > 85%")
    print_metric_row("Recall@5 (Hit@5)", f"{summary['recall_at_5'] * 100:.1f}%", "Target: > 90%")
    print_metric_row("Mean Reciprocal Rank (MRR)", f"{summary['mrr']:.4f}", "Target: > 0.85")
    print_metric_row("NDCG@5", f"{summary['ndcg_at_5']:.4f}", "Target: > 0.85")

    # ── 3. Latency & Systems Performance ──
    print_banner("3. LATENCY DISTRIBUTION & THROUGHPUT")
    ret_lat = ir_metrics["retrieval_latency_profile"]
    cls_lat = cls_metrics["classifier_latency_profile"]
    emb_lat = perf_metrics["embedding_latency"]
    llm_lat = perf_metrics["llm_inference_latency"]
    e2e_lat = perf_metrics["end_to_end_pipeline_latency"]
    tput = perf_metrics["throughput"]

    print(f"  {'Stage':<28} {'p50 (ms)':<12} {'p90 (ms)':<12} {'p95 (ms)':<12} {'p99 (ms)':<12} {'Mean (ms)':<12}")
    print(f"  {'-'*28} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    print(f"  {'Classifier Inference':<28} {cls_lat['p50']:<12} {cls_lat['p90']:<12} {cls_lat['p95']:<12} {cls_lat['p99']:<12} {cls_lat['mean']:<12}")
    print(f"  {'Embedding Generation':<28} {emb_lat['p50']:<12} {emb_lat['p90']:<12} {emb_lat['p95']:<12} {emb_lat['p99']:<12} {emb_lat['mean']:<12}")
    print(f"  {'Vector Search (Top-10)':<28} {ret_lat['p50']:<12} {ret_lat['p90']:<12} {ret_lat['p95']:<12} {ret_lat['p99']:<12} {ret_lat['mean']:<12}")
    print(f"  {'LLM RAG Synthesis':<28} {llm_lat['p50']:<12} {llm_lat['p90']:<12} {llm_lat['p95']:<12} {llm_lat['p99']:<12} {llm_lat['mean']:<12}")
    print(f"  {'End-to-End Pipeline':<28} {e2e_lat['p50']:<12} {e2e_lat['p90']:<12} {e2e_lat['p95']:<12} {e2e_lat['p99']:<12} {e2e_lat['mean']:<12}")

    print()
    print_metric_row("Pipeline Burst Throughput", f"{tput['events_per_second']} eps", "Target: > 50 eps")
    print_metric_row("E2E Pipeline p95 Latency", f"{e2e_lat['p95']} ms", "Target: < 50 ms")

    # ── Save Results to JSON ──
    out_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n  \033[1;32m✔ Results saved successfully to {out_path}\033[0m\n")


if __name__ == "__main__":
    asyncio.run(main())
