"""
LayaPulse Evaluation Harness.

Orchestrates complete benchmarks across:
1. Topic Classification (12 categories)
2. Sentiment Classification (positive, neutral, negative)
3. Information Retrieval / RAG (Precision@K, Recall@K, MRR, NDCG)
4. Latency Distribution Profiling (Retrieval, Classifier, Embedder, LLM, End-to-End Pipeline)
5. Throughput Profiling (events / second)
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from database import init_db, async_session, Post, Classification, Hashtag, Entity, MentionedUser, ExtractedUrl, EmbeddingRecord
from eval_dataset import BENCHMARK_POSTS, BENCHMARK_RAG_QUERIES
from eval_metrics import (
    compute_classification_metrics,
    compute_retrieval_benchmarks,
    compute_latency_distribution,
)
from mock_providers import (
    MockEmbeddingProvider,
    MockLayaClassifier,
    MockLLMProvider,
    MockVectorStore,
)
from pipeline import PostProcessingPipeline
from schemas import RawPost


class EvaluationHarness:
    """Automated benchmark and evaluation harness for LayaPulse."""

    def __init__(self) -> None:
        self.classifier = MockLayaClassifier()
        self.embedder = MockEmbeddingProvider(dim=384)
        self.vector_store = MockVectorStore()
        self.llm = MockLLMProvider()

    async def run_classification_eval(self) -> Dict[str, Any]:
        """Runs classification benchmarks for Topic and Sentiment."""
        topic_true: List[str] = []
        topic_pred: List[str] = []
        sentiment_true: List[str] = []
        sentiment_pred: List[str] = []

        latencies_ms: List[float] = []

        for item in BENCHMARK_POSTS:
            t0 = time.perf_counter()
            res = await self.classifier.classify(item["text"])
            lat_ms = (time.perf_counter() - t0) * 1000
            latencies_ms.append(lat_ms)

            topic_true.append(item["category"])
            topic_pred.append(res.category)

            sentiment_true.append(item["sentiment"])
            sentiment_pred.append(res.sentiment)

        categories = [
            "AI", "Machine Learning", "Technology", "Startups", "Finance",
            "Politics", "Sports", "Science", "Cybersecurity", "Climate",
            "Gaming", "Other",
        ]
        topic_metrics = compute_classification_metrics(topic_true, topic_pred, labels=categories)

        sentiments = ["positive", "neutral", "negative"]
        sentiment_metrics = compute_classification_metrics(sentiment_true, sentiment_pred, labels=sentiments)

        return {
            "topic_classification": topic_metrics,
            "sentiment_classification": sentiment_metrics,
            "classifier_latency_profile": compute_latency_distribution(latencies_ms),
        }

    async def run_retrieval_eval(self) -> Dict[str, Any]:
        """Indexes benchmark posts and evaluates IR / RAG retrieval metrics."""
        # 1. Fresh vector store for clean evaluation
        eval_vector_store = MockVectorStore()

        # Index all 120 posts
        for post in BENCHMARK_POSTS:
            vector = await self.embedder.embed(post["text"])
            await eval_vector_store.add(
                embedding_id=post["id"],
                vector=vector,
                metadata={
                    "post_id": post["id"],
                    "text": post["text"],
                    "category": post["category"],
                    "author": post["author"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        query_evals: List[Dict[str, Any]] = []
        retrieval_latencies: List[float] = []

        for q in BENCHMARK_RAG_QUERIES:
            t0 = time.perf_counter()
            q_vec = await self.embedder.embed(q["question"])
            results = await eval_vector_store.search(q_vec, top_k=15)
            lat_ms = (time.perf_counter() - t0) * 1000
            retrieval_latencies.append(lat_ms)

            retrieved_ids = [eid for eid, _, _ in results]
            query_evals.append({
                "query_id": q["query_id"],
                "question": q["question"],
                "retrieved_ids": retrieved_ids,
                "relevant_ids": q["relevant_ids"],
            })

        retrieval_metrics = compute_retrieval_benchmarks(query_evals, k_values=(1, 3, 5, 10))
        retrieval_metrics["retrieval_latency_profile"] = compute_latency_distribution(retrieval_latencies)

        return retrieval_metrics

    async def run_latency_and_throughput_eval(self, num_samples: int = 100) -> Dict[str, Any]:
        """
        Profiles exact execution latencies for each pipeline component and
        end-to-end streaming ingestion.
        """
        await init_db()

        # 1. Embedder latency profiling
        embed_latencies: List[float] = []
        sample_texts = [p["text"] for p in BENCHMARK_POSTS[:num_samples]]
        for txt in sample_texts:
            t0 = time.perf_counter()
            await self.embedder.embed(txt)
            embed_latencies.append((time.perf_counter() - t0) * 1000)

        # 2. LLM synthesis latency profiling
        llm_latencies: List[float] = []
        for q in BENCHMARK_RAG_QUERIES:
            sample_ctx = "Author: @demis_hassabis\nText: DeepMind releases Gemini 2.0."
            t0 = time.perf_counter()
            await self.llm.generate(prompt=q["question"], context=sample_ctx)
            llm_latencies.append((time.perf_counter() - t0) * 1000)

        # 3. Vector search latency profiling (isolated)
        search_latencies: List[float] = []
        dummy_vec = await self.embedder.embed("benchmark query vector")
        for _ in range(num_samples):
            t0 = time.perf_counter()
            await self.vector_store.search(dummy_vec, top_k=10)
            search_latencies.append((time.perf_counter() - t0) * 1000)

        # 4. End-to-end processing pipeline profiling
        pipeline_latencies: List[float] = []
        test_pipeline = PostProcessingPipeline(self.classifier, self.embedder, self.vector_store)

        for i, p in enumerate(BENCHMARK_POSTS[:num_samples]):
            raw = RawPost(
                external_id=f"bench_e2e_{i}_{uuid.uuid4().hex[:6]}",
                author_name=p["author"],
                author_username=p["author"],
                author_avatar="https://api.dicebear.com/7.x/initials/svg?seed=BP",
                text=p["text"],
                timestamp=datetime.utcnow(),
                url=f"https://x.com/{p['author']}/status/12345678",
                likes=100,
                reposts=25,
                replies=10,
                views=1500,
            )

            t0 = time.perf_counter()
            await test_pipeline._process(raw)
            e2e_ms = (time.perf_counter() - t0) * 1000
            pipeline_latencies.append(e2e_ms)

        # 5. Throughput test (multi-worker pipeline burst)
        burst_posts = [
            RawPost(
                external_id=f"burst_{i}_{uuid.uuid4().hex[:6]}",
                author_name=BENCHMARK_POSTS[i % len(BENCHMARK_POSTS)]["author"],
                author_username=BENCHMARK_POSTS[i % len(BENCHMARK_POSTS)]["author"],
                author_avatar="https://api.dicebear.com/7.x/initials/svg?seed=BP",
                text=BENCHMARK_POSTS[i % len(BENCHMARK_POSTS)]["text"],
                timestamp=datetime.utcnow(),
            )
            for i in range(100)
        ]

        throughput_pipeline = PostProcessingPipeline(self.classifier, self.embedder, self.vector_store)
        await throughput_pipeline.start(num_workers=4)

        burst_start = time.perf_counter()
        for post in burst_posts:
            await throughput_pipeline.enqueue(post)

        # Wait until all burst posts are fully processed
        timeout = 10.0
        start_wait = time.time()
        while throughput_pipeline.stats.posts_analyzed < len(burst_posts) and (time.time() - start_wait) < timeout:
            await asyncio.sleep(0.01)

        burst_duration = time.perf_counter() - burst_start
        await throughput_pipeline.stop()

        throughput_eps = len(burst_posts) / burst_duration if burst_duration > 0 else 0.0

        return {
            "embedding_latency": compute_latency_distribution(embed_latencies),
            "vector_search_latency": compute_latency_distribution(search_latencies),
            "llm_inference_latency": compute_latency_distribution(llm_latencies),
            "end_to_end_pipeline_latency": compute_latency_distribution(pipeline_latencies),
            "throughput": {
                "total_events_processed": len(burst_posts),
                "duration_seconds": round(burst_duration, 3),
                "events_per_second": round(throughput_eps, 1),
            },
        }

    async def run_full_suite(self) -> Dict[str, Any]:
        """Runs the entire evaluation benchmark suite and returns consolidated results."""
        start_time = datetime.utcnow().isoformat() + "Z"

        cls_results = await self.run_classification_eval()
        ir_results = await self.run_retrieval_eval()
        perf_results = await self.run_latency_and_throughput_eval()

        return {
            "timestamp": start_time,
            "suite_version": "1.0.0",
            "summary": {
                "sentiment_f1": cls_results["sentiment_classification"]["macro_f1"],
                "topic_f1": cls_results["topic_classification"]["macro_f1"],
                "precision_at_1": ir_results["precision@1"],
                "precision_at_3": ir_results["precision@3"],
                "precision_at_5": ir_results["precision@5"],
                "recall_at_1": ir_results["recall@1"],
                "recall_at_3": ir_results["recall@3"],
                "recall_at_5": ir_results["recall@5"],
                "mrr": ir_results["mrr"],
                "ndcg_at_5": ir_results["ndcg@5"],
                "retrieval_latency_p50_ms": ir_results["retrieval_latency_profile"]["p50"],
                "retrieval_latency_p95_ms": ir_results["retrieval_latency_profile"]["p95"],
                "classifier_latency_p50_ms": cls_results["classifier_latency_profile"]["p50"],
                "classifier_latency_p95_ms": cls_results["classifier_latency_profile"]["p95"],
                "embedding_latency_p50_ms": perf_results["embedding_latency"]["p50"],
                "end_to_end_latency_p50_ms": perf_results["end_to_end_pipeline_latency"]["p50"],
                "end_to_end_latency_p95_ms": perf_results["end_to_end_pipeline_latency"]["p95"],
                "throughput_events_per_second": perf_results["throughput"]["events_per_second"],
            },
            "classification": cls_results,
            "retrieval": ir_results,
            "performance": perf_results,
        }
