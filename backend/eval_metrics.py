"""
Evaluation metrics calculation engine for LayaPulse.

Implements rigorous empirical metrics without third-party heavy dependencies:
- Multiclass Classification: Macro F1, Weighted F1, Micro F1, Accuracy, Confusion Matrix, Per-class metrics
- Information Retrieval: Precision@K, Recall@K, HitRate@K, MRR, MAP, NDCG@K
- Latency & Systems: p50, p90, p95, p99, mean, stddev, min, max
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
#  CLASSIFICATION METRICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Computes precision, recall, F1, accuracy, and confusion matrix.
    Supports both multiclass and multi-label evaluations.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have identical length")

    if labels is None:
        all_labels = sorted(list(set(y_true) | set(y_pred)))
    else:
        all_labels = list(labels)

    total_samples = len(y_true)
    if total_samples == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "weighted_f1": 0.0}

    # Accuracy
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / total_samples

    # Confusion Matrix: matrix[true_idx][pred_idx]
    label_to_idx = {l: i for i, l in enumerate(all_labels)}
    k = len(all_labels)
    cm = [[0] * k for _ in range(k)]

    for yt, yp in zip(y_true, y_pred):
        ti = label_to_idx.get(yt)
        pi = label_to_idx.get(yp)
        if ti is not None and pi is not None:
            cm[ti][pi] += 1

    per_class: Dict[str, Dict[str, float]] = {}
    macro_p, macro_r, macro_f1 = 0.0, 0.0, 0.0
    weighted_p, weighted_r, weighted_f1 = 0.0, 0.0, 0.0

    for i, label in enumerate(all_labels):
        tp = cm[i][i]
        fp = sum(cm[row][i] for row in range(k)) - tp
        fn = sum(cm[i][col] for col in range(k)) - tp
        support = tp + fn

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class[label] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }

        macro_p += prec
        macro_r += rec
        macro_f1 += f1

        weight = support / total_samples
        weighted_p += prec * weight
        weighted_r += rec * weight
        weighted_f1 += f1 * weight

    num_classes = len(all_labels) if len(all_labels) > 0 else 1

    return {
        "total_samples": total_samples,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_p / num_classes, 4),
        "macro_recall": round(macro_r / num_classes, 4),
        "macro_f1": round(macro_f1 / num_classes, 4),
        "weighted_precision": round(weighted_p, 4),
        "weighted_recall": round(weighted_r, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "labels": all_labels,
        "confusion_matrix": cm,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  INFORMATION RETRIEVAL / RAG METRICS
# ═══════════════════════════════════════════════════════════════════════════

def precision_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """Computes Precision@K: relevant items in top-K / K."""
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k


def recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """Computes Recall@K: relevant items in top-K / total relevant."""
    if not relevant or k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def hit_rate_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """Computes Hit Rate@K: 1 if at least one relevant item in top-K else 0."""
    top_k = retrieved[:k]
    return 1.0 if any(item in relevant for item in top_k) else 0.0


def reciprocal_rank(retrieved: Sequence[str], relevant: Set[str]) -> float:
    """Computes Reciprocal Rank (1/rank of first relevant item)."""
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def average_precision(retrieved: Sequence[str], relevant: Set[str]) -> float:
    """Computes Average Precision across full retrieved list."""
    if not relevant:
        return 0.0
    hits = 0
    sum_precisions = 0.0
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            hits += 1
            sum_precisions += hits / rank
    return sum_precisions / len(relevant)


def ndcg_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """
    Computes Normalized Discounted Cumulative Gain (NDCG@K) with binary relevance.
    DCG@K = sum_{i=1}^K rel_i / log2(i + 1)
    IDCG@K = sum_{i=1}^{min(K, |rel|)} 1 / log2(i + 1)
    """
    if not relevant or k <= 0:
        return 0.0

    top_k = retrieved[:k]
    dcg = 0.0
    for i, item in enumerate(top_k, start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(i + 1)

    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

    return dcg / idcg if idcg > 0 else 0.0


def compute_retrieval_benchmarks(
    query_evaluations: List[Dict[str, Any]],
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> Dict[str, Any]:
    """
    Aggregates Precision@K, Recall@K, HitRate@K, MRR, MAP, NDCG@K across all benchmark queries.
    query_evaluations format: [{"retrieved_ids": [...], "relevant_ids": [...]}, ...]
    """
    num_queries = len(query_evaluations)
    if num_queries == 0:
        return {}

    precisions: Dict[int, List[float]] = {k: [] for k in k_values}
    recalls: Dict[int, List[float]] = {k: [] for k in k_values}
    hit_rates: Dict[int, List[float]] = {k: [] for k in k_values}
    ndcgs: Dict[int, List[float]] = {k: [] for k in k_values}
    rrs: List[float] = []
    aps: List[float] = []

    for q in query_evaluations:
        retrieved = q["retrieved_ids"]
        relevant = set(q["relevant_ids"])

        for k in k_values:
            precisions[k].append(precision_at_k(retrieved, relevant, k))
            recalls[k].append(recall_at_k(retrieved, relevant, k))
            hit_rates[k].append(hit_rate_at_k(retrieved, relevant, k))
            ndcgs[k].append(ndcg_at_k(retrieved, relevant, k))

        rrs.append(reciprocal_rank(retrieved, relevant))
        aps.append(average_precision(retrieved, relevant))

    results: Dict[str, Any] = {
        "num_queries": num_queries,
        "mrr": round(float(np.mean(rrs)), 4),
        "map": round(float(np.mean(aps)), 4),
    }

    for k in k_values:
        results[f"precision@{k}"] = round(float(np.mean(precisions[k])), 4)
        results[f"recall@{k}"] = round(float(np.mean(recalls[k])), 4)
        results[f"hit_rate@{k}"] = round(float(np.mean(hit_rates[k])), 4)
        results[f"ndcg@{k}"] = round(float(np.mean(ndcgs[k])), 4)

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  LATENCY & SYSTEMS PROFILING
# ═══════════════════════════════════════════════════════════════════════════

def compute_latency_distribution(latencies_ms: Sequence[float]) -> Dict[str, float]:
    """Calculates statistical latency percentiles and distribution metrics in ms."""
    if not latencies_ms:
        return {
            "count": 0,
            "mean": 0.0,
            "stddev": 0.0,
            "min": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        }

    arr = np.array(latencies_ms, dtype=np.float64)
    return {
        "count": len(arr),
        "mean": round(float(np.mean(arr)), 2),
        "stddev": round(float(np.std(arr)), 2),
        "min": round(float(np.min(arr)), 2),
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p90": round(float(np.percentile(arr, 90)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
        "max": round(float(np.max(arr)), 2),
    }
