"""
Mock implementations of all provider interfaces.
Enables a fully functional demo without any external API keys.
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import numpy as np

from config import settings
from providers import EmbeddingProvider, LayaClassifier, LLMProvider, StreamProvider, VectorStore
from schemas import ClassificationResult, EntityInfo, RawPost


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK AUTHORS
# ═══════════════════════════════════════════════════════════════════════════
MOCK_AUTHORS = [
    {"name": "Sam Altman", "username": "sama", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=SA&backgroundColor=6366f1"},
    {"name": "Yann LeCun", "username": "ylecun", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=YL&backgroundColor=ec4899"},
    {"name": "Andrej Karpathy", "username": "karpathy", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=AK&backgroundColor=14b8a6"},
    {"name": "Demis Hassabis", "username": "demabordi", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=DH&backgroundColor=f97316"},
    {"name": "TechCrunch", "username": "TechCrunch", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=TC&backgroundColor=22c55e"},
    {"name": "The Verge", "username": "verge", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=TV&backgroundColor=3b82f6"},
    {"name": "Lex Fridman", "username": "lexfridman", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=LF&backgroundColor=a855f7"},
    {"name": "Elon Musk", "username": "elonmusk", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=EM&backgroundColor=64748b"},
    {"name": "Jensen Huang", "username": "jensen_huang", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=JH&backgroundColor=84cc16"},
    {"name": "Satya Nadella", "username": "satabordi", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=SN&backgroundColor=06b6d4"},
    {"name": "Reuters Tech", "username": "ReutersTech", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=RT&backgroundColor=f43f5e"},
    {"name": "MIT Tech Review", "username": "techreview", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=MT&backgroundColor=8b5cf6"},
    {"name": "Benedict Evans", "username": "benedictevans", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=BE&backgroundColor=0ea5e9"},
    {"name": "Naval", "username": "naval", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=NR&backgroundColor=d946ef"},
    {"name": "Casey Newton", "username": "CaseyNewton", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=CN&backgroundColor=eab308"},
    {"name": "AI Researcher", "username": "ai_researcher", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=AR&backgroundColor=10b981"},
    {"name": "Crypto Analyst", "username": "crypto_alpha", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=CA&backgroundColor=f59e0b"},
    {"name": "Climate Tracker", "username": "climate_now", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=CT&backgroundColor=22d3ee"},
    {"name": "GameDev Daily", "username": "gamedev_daily", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=GD&backgroundColor=fb923c"},
    {"name": "CyberSec Alert", "username": "cybersec_alert", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=CS&backgroundColor=ef4444"},
]


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK POST TEMPLATES  (category → list of templates)
# ═══════════════════════════════════════════════════════════════════════════
MOCK_POSTS: Dict[str, List[str]] = {
    "AI": [
        "🚀 Just released: New multimodal AI model achieves state-of-the-art results on every major benchmark. This changes everything. #AI #MachineLearning",
        "The new reasoning capabilities in GPT-5 are genuinely impressive. Tested it on complex math proofs and it nailed problems that stumped previous models. @OpenAI",
        "Breaking: Google DeepMind announces Gemini Ultra 2.0 with unprecedented performance on scientific reasoning tasks. Paper drops tomorrow. #AI #DeepMind",
        "Hot take: AI agents are overhyped right now. Most 'autonomous agents' are just prompt chains with retry logic. Real autonomy requires better planning. #AI",
        "Interesting observation: AI model sizes are plateauing but capabilities keep improving. Efficiency gains > scale at this point. #AI #Research",
        "BREAKING: Anthropic releases Claude 5 with 1M context window and native code execution. Early benchmarks show 40% improvement over previous gen. #AI",
        "The AI safety debate is shifting. More researchers now argue that capability controls matter more than alignment training. Important paper: arxiv.org/abs/2024.1234",
        "Just tested the new open-source LLM from Meta — Llama 4 is genuinely competitive with closed-source models now. The gap is closing fast. #OpenSource #AI",
        "AI-generated code now passes 94% of real-world software engineering tasks in the SWE-bench. We're approaching a tipping point for developer tools. #AI #Coding",
        "New study: AI systems trained on synthetic data outperform those trained on real data for specific domains. This could solve the data bottleneck. #AI #ML",
    ],
    "Machine Learning": [
        "New paper: Transformers can be replaced by state-space models for 80% of NLP tasks with 10x less compute. Huge implications for efficiency. #ML #Research",
        "Finally got my fine-tuned model working on edge devices. 3B parameters running at 60 tokens/sec on a phone GPU. The future is local inference. #ML",
        "Interesting trend: mixture-of-experts architectures are becoming the default for large models. Sparse activation is the key to scaling. #MachineLearning",
        "Published our research on continual learning without catastrophic forgetting. We achieved 95% retention across 50 sequential tasks. #ML #Research",
        "The debate between RL and supervised fine-tuning continues. Our experiments show RLHF still wins for complex reasoning, but DPO is catching up. #ML",
        "New breakthrough in diffusion models: we can now generate 4K images in under 2 seconds. Consistency models + architectural innovations. #ML #GenAI",
    ],
    "Technology": [
        "Apple announces Vision Pro 2 with 8K displays and neural interface support. Ships Q1 next year. The spatial computing era is accelerating. #Apple #Tech",
        "Major acquisition: Microsoft buys a leading robotics company for $12B. Satya says 'physical AI is the next frontier.' #Microsoft #Tech",
        "The EU AI Act enforcement begins next month. Companies scrambling to comply. This will reshape how tech is built in Europe. #Regulation #Tech",
        "Starlink now has 5 million subscribers globally. Internet access in remote areas has increased 300% in regions with coverage. #SpaceX #Tech",
        "Quantum computing milestone: IBM achieves 1,000 logical qubits with error correction. Commercial quantum advantage is now 2-3 years away. #Quantum #Tech",
        "Tech layoffs continue: 15,000 jobs cut across major companies this month. But AI-related hiring is up 200%. The industry is reshaping fast. #Tech #Jobs",
    ],
    "Startups": [
        "Just closed our Series B: $85M to build the next generation of AI infrastructure. Grateful for the team and investors who believe in our vision. #Startup",
        "Y Combinator's latest batch is 70% AI companies. The concentration is unprecedented. Is this a bubble or a paradigm shift? #YC #Startups",
        "Hot take: Most AI startups will fail because they're building wrappers, not moats. The ones with proprietary data will survive. #Startups #AI",
        "Announced today: Our dev tools startup hit $10M ARR in 11 months. Product-led growth in developer tools is real. #Startup #DevTools",
        "The startup funding landscape is bifurcating: AI companies getting massive rounds, everything else struggling. Seen 3 shutdowns this week. #Startups #VC",
    ],
    "Finance": [
        "BREAKING: Fed announces surprise rate cut of 50 basis points. Markets surge 3% in after-hours trading. #Finance #Markets",
        "Bitcoin breaks $150,000 for the first time. Institutional adoption accelerating as ETF inflows hit record levels. #Crypto #Bitcoin #Finance",
        "Q3 earnings surprise: Tech sector beats expectations by 15% on average. AI-driven revenue growth cited by every major company. #Finance #Earnings",
        "Warning: Commercial real estate defaults hitting levels not seen since 2008. Banks tightening lending standards. #Finance #RealEstate",
        "NVIDIA market cap surpasses $5 trillion, becoming the world's most valuable company. AI chip demand shows no signs of slowing. #NVDA #Finance",
    ],
    "Cybersecurity": [
        "🚨 CRITICAL: Zero-day vulnerability discovered in major enterprise software. Patch immediately. CVE-2024-9999 affects millions of systems. #CyberSec",
        "Major data breach at a Fortune 500 company exposes 50M customer records. Investigation suggests state-sponsored actors. #CyberSecurity #DataBreach",
        "New ransomware variant uses AI to adapt its encryption patterns, making traditional detection methods obsolete. Security teams need new approaches. #CyberSec",
        "Our security team just published findings on a new supply-chain attack vector targeting npm packages. 200+ packages compromised. #CyberSecurity #DevSec",
        "NIST releases updated cybersecurity framework with AI-specific guidelines. About time. Every organization should review these. #CyberSec #NIST",
    ],
    "Science": [
        "Breakthrough: New CRISPR technique allows precise editing of mitochondrial DNA for the first time. Could treat dozens of genetic diseases. #Science #Biotech",
        "NASA confirms discovery of biosignatures in Enceladus ocean samples. This could be the most significant scientific finding of the century. #Science #Space",
        "New fusion reactor design achieves net energy gain for 30 continuous minutes. Commercial fusion power within a decade? #Science #Energy",
        "Published in Nature: AI-designed proteins fold with 99.9% accuracy. Drug discovery timelines could shrink from years to months. #Science #AI",
    ],
    "Climate": [
        "Global temperatures hit new record for the 15th consecutive month. Scientists warn tipping points may be closer than predicted. #Climate #Environment",
        "Major breakthrough in direct air capture: new catalyst reduces cost by 80%. Carbon removal at scale becoming economically viable. #Climate #CleanTech",
        "Renewable energy now generates 45% of global electricity, up from 30% just 3 years ago. Solar costs dropped another 20% this year. #Climate #Energy",
        "Arctic sea ice reaches lowest extent ever recorded. The feedback loops are accelerating faster than models predicted. #Climate #Science",
    ],
    "Politics": [
        "Breaking: New legislation proposed to regulate AI development. Bipartisan support suggests it could pass this session. #Politics #AIRegulation",
        "Tech antitrust hearings continue: CEOs testify on market concentration and data practices. Potential breakup orders on the table. #Politics #Tech",
        "International AI safety treaty signed by 40 nations. Establishes compute thresholds and mandatory safety testing. Historic moment. #Politics #AISafety",
        "Election security concerns: Deepfake detection tools deployed across social media platforms ahead of upcoming elections. #Politics #AI #Elections",
    ],
    "Sports": [
        "AI analytics revolution: NBA team uses real-time computer vision to make in-game tactical adjustments. Won 12 straight games. #Sports #AI",
        "FIFA announces AI-powered refereeing system for 2026 World Cup. Uses 200 cameras and real-time tracking. #Sports #Tech",
        "Esports viewership surpasses NFL for 18-34 demographic. The shift in entertainment is undeniable. #Sports #Esports #Gaming",
    ],
    "Gaming": [
        "NVIDIA announces next-gen RTX 6090 with AI-powered real-time ray tracing. 3x performance jump. Gamers, get your wallets ready. #Gaming #NVIDIA",
        "Unreal Engine 6 teaser shows AI-generated NPCs with persistent memory and emotional responses. Game design will never be the same. #Gaming #AI",
        "New study: AI-generated game content indistinguishable from human-created content in blind tests. Procedural generation reaches new heights. #Gaming",
        "Steam Deck 2 announced with neural processing unit for on-device AI features. Portable gaming enters the AI era. #Gaming #Valve",
    ],
}

# Mapping of keywords to entities for extraction
ENTITY_MAP: Dict[str, Tuple[str, str]] = {
    "openai": ("OpenAI", "ORG"),
    "google": ("Google", "ORG"),
    "deepmind": ("DeepMind", "ORG"),
    "anthropic": ("Anthropic", "ORG"),
    "meta": ("Meta", "ORG"),
    "microsoft": ("Microsoft", "ORG"),
    "apple": ("Apple", "ORG"),
    "nvidia": ("NVIDIA", "ORG"),
    "tesla": ("Tesla", "ORG"),
    "spacex": ("SpaceX", "ORG"),
    "amazon": ("Amazon", "ORG"),
    "ibm": ("IBM", "ORG"),
    "nasa": ("NASA", "ORG"),
    "nist": ("NIST", "ORG"),
    "fifa": ("FIFA", "ORG"),
    "nba": ("NBA", "ORG"),
    "valve": ("Valve", "ORG"),
    "gpt": ("GPT", "PRODUCT"),
    "gpt-5": ("GPT-5", "PRODUCT"),
    "gemini": ("Gemini", "PRODUCT"),
    "claude": ("Claude", "PRODUCT"),
    "llama": ("Llama", "PRODUCT"),
    "starlink": ("Starlink", "PRODUCT"),
    "vision pro": ("Vision Pro", "PRODUCT"),
    "steam deck": ("Steam Deck", "PRODUCT"),
    "unreal engine": ("Unreal Engine", "PRODUCT"),
    "transformer": ("Transformer", "TECH"),
    "diffusion": ("Diffusion Models", "TECH"),
    "crispr": ("CRISPR", "TECH"),
    "blockchain": ("Blockchain", "TECH"),
    "bitcoin": ("Bitcoin", "TECH"),
    "quantum": ("Quantum Computing", "TECH"),
    "rlhf": ("RLHF", "TECH"),
    "sam altman": ("Sam Altman", "PERSON"),
    "satya": ("Satya Nadella", "PERSON"),
    "jensen": ("Jensen Huang", "PERSON"),
    "elon": ("Elon Musk", "PERSON"),
}

# Sentiment keywords
POSITIVE_WORDS = {
    "breakthrough", "amazing", "impressive", "achieves", "surpasses", "milestone",
    "incredible", "revolutionary", "success", "record", "best", "greatest",
    "excellent", "brilliant", "outstanding", "remarkable", "grateful", "thrilled",
    "unprecedented", "historic", "exciting", "wow", "fantastic", "improvement",
    "solved", "innovation", "accelerating", "beats", "won", "grows", "proud",
    "surges", "stellar", "celebrated", "celebrating", "wonderful", "sensational",
    "triumph", "delicious", "heartwarming", "charming", "breathtaking",
    "unbelievable", "masterpiece", "exceptional", "recovers", "dismantles",
}
NEGATIVE_WORDS = {
    "warning", "critical", "breach", "vulnerability", "fails", "crash", "crashes",
    "layoffs", "shutdown", "default", "defaults", "attack", "threat", "threatens",
    "concern", "scrambling", "struggling", "fear", "risk", "decline", "worst",
    "devastating", "alarming", "dangerous", "collapse", "crisis", "cut",
    "ransomware", "compromised", "expose", "exposes", "lowest", "brutal",
    "panic", "ruined", "disruptions", "disastrous", "humiliating", "floods",
    "litigation", "adversarial", "jailbreak", "hallucination", "explosion",
    "leakage", "corruption", "scandal", "doping", "retracted", "mega-drought",
    "acidification", "predatory", "terrible", "outage", "disables", "malfunction",
}


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK STREAM PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class MockStreamProvider(StreamProvider):
    """Generates realistic mock X/Twitter posts at a configurable interval."""

    def __init__(self, interval: float = 2.5) -> None:
        self._interval = interval
        self._running = True
        self._post_index = 0

    async def stream(self) -> AsyncIterator[RawPost]:
        while self._running:
            # Pick a random category and post template
            category = random.choice(list(MOCK_POSTS.keys()))
            template = random.choice(MOCK_POSTS[category])
            author = random.choice(MOCK_AUTHORS)

            self._post_index += 1
            post = RawPost(
                external_id=f"mock_{uuid.uuid4().hex[:12]}",
                author_name=author["name"],
                author_username=author["username"],
                author_avatar=author["avatar"],
                text=template,
                timestamp=datetime.utcnow(),
                url=f"https://x.com/{author['username']}/status/{random.randint(10**17, 10**18)}",
                likes=random.randint(0, 50000),
                reposts=random.randint(0, 15000),
                replies=random.randint(0, 5000),
                views=random.randint(1000, 5000000),
            )
            yield post

            # Vary the interval slightly for realism
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(self._interval * jitter)

    async def stop(self) -> None:
        self._running = False


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK LAYA CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════
class MockLayaClassifier(LayaClassifier):
    """
    Keyword‑based classifier that mimics Laya decision outputs.
    Uses text analysis to determine category, sentiment, importance, etc.
    """

    def __init__(self) -> None:
        self._categories = list(settings.default_categories)
        self._category_keywords: Dict[str, List[str]] = {
            "AI": ["ai", "artificial intelligence", "llm", "deepmind", "gemini", "chatgpt", "gpt", "chatbot", "claude", "anthropic", "openai", "reasoning", "alignment", "agi", "speculative decoding", "prompt caching", "hallucination"],
            "Machine Learning": ["machine learning", "ml", "fine-tuning", "state-space", "transformer", "diffusion", "rlhf", "dpo", "continual learning", "catastrophic forgetting", "lora", "mixture-of-experts", "moe", "flashattention", "quantization", "fp4"],
            "Technology": ["apple", "vision pro", "microsoft", "robotics", "ibm", "quantum", "qubit", "starlink", "broadband", "satellite", "usb-c", "tsmc", "gaa", "semiconductor", "tensor processing unit", "silicon photonics", "firmware", "hardware"],
            "Startups": ["startup", "startups", "series b", "series a", "y combinator", "yc", "arr", "burn rate", "safe note", "founder", "receivership", "venture capital", "seed stage", "seed funding", "b2b saas"],
            "Finance": ["bitcoin", "crypto", "etf", "federal reserve", "interest rate", "nvidia", "earnings", "inflation", "treasury", "yield curve", "share buybacks", "hedge fund", "sovereign credit", "foreign exchange", "gdp"],
            "Politics": ["senate", "bipartisan", "legislation", "government shutdown", "supreme court", "scotus", "climate treaty", "sanctions", "trade sanctions", "electoral", "referendum", "diplomatic summit", "antitrust"],
            "Sports": ["nba", "buzzer-beater", "finals", "quarterback", "nfl", "fifa", "world cup", "marathon", "grand slam", "premier league", "olympic", "doping", "formula 1", "fia", "tennis"],
            "Science": ["james webb", "biosignature", "exoplanet", "superconductivity", "nature", "genomic", "epigenetic", "crispr", "congenital", "cern", "particle accelerator", "nuclear fusion", "fusion", "antibiotic resistance", "hydrothermal", "solid-state battery"],
            "Cybersecurity": ["zero-day", "cve", "firewall", "ransomware", "data breach", "breach", "memory-safe", "supply-chain attack", "npm", "post-quantum", "nist", "ddos", "malware", "phishing", "side-channel"],
            "Climate": ["renewable", "solar", "wind", "mega-drought", "carbon dioxide", "direct air capture", "monsoon", "ocean circulation", "reforestation", "mangrove", "ocean acidification", "green hydrogen", "co2", "ipcc"],
            "Gaming": ["unreal engine", "unreal", "steam", "game of the year", "role-playing", "rpg", "procedural world", "virtual reality", "microtransactions", "esports", "gaming", "retro gaming"],
        }

    async def classify(self, text: str, metadata: Dict[str, Any] | None = None) -> ClassificationResult:
        text_lower = text.lower()
        words_list = re.findall(r"\b\w+\b", text_lower)
        words_set = set(words_list)

        # ── Category detection ──
        scores: Dict[str, int] = {}
        for cat, keywords in self._category_keywords.items():
            cat_score = 0
            for kw in keywords:
                if " " in kw or "-" in kw:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                        cat_score += 4
                else:
                    if kw in words_set:
                        cat_score += 2
            scores[cat] = cat_score

        category = max(scores, key=scores.get) if max(scores.values()) > 0 else "Other"

        # ── Sentiment ──
        pos = sum(1 for w in POSITIVE_WORDS if (w in words_set) or ((" " in w or "-" in w) and (w in text_lower)))
        neg = sum(1 for w in NEGATIVE_WORDS if (w in words_set) or ((" " in w or "-" in w) and (w in text_lower)))
        if pos > neg:
            sentiment = "positive"
            sentiment_score = min(1.0, 0.3 + pos * 0.15)
        elif neg > pos:
            sentiment = "negative"
            sentiment_score = max(-1.0, -0.3 - neg * 0.15)
        else:
            sentiment = "neutral"
            sentiment_score = 0.0

        # ── Relevance (0‑100) ──
        relevance = min(100, 40 + scores.get(category, 0) * 15 + random.randint(0, 20))

        # ── Importance ──
        has_breaking = any(w in text_lower for w in ["breaking", "critical", "🚨", "major", "milestone", "unprecedented", "historic"])
        importance_score = relevance * 0.5 + (30 if has_breaking else 0) + random.randint(0, 15)
        importance_score = min(100, importance_score)
        if importance_score >= 85:
            importance = "CRITICAL"
        elif importance_score >= 65:
            importance = "HIGH"
        elif importance_score >= 40:
            importance = "MEDIUM"
        else:
            importance = "LOW"

        should_alert = importance in ("CRITICAL", "HIGH") and relevance >= 75
        is_significant = importance == "CRITICAL" or (importance == "HIGH" and has_breaking)

        # ── Entity extraction ──
        entities = []
        for keyword, (name, etype) in ENTITY_MAP.items():
            if keyword in text_lower:
                entities.append(EntityInfo(name=name, entity_type=etype))

        # ── Explanation ──
        reasons = []
        if has_breaking:
            reasons.append("contains breaking/critical language indicators")
        if scores.get(category, 0) > 2:
            reasons.append(f"strong keyword match for {category} ({scores[category]} indicators)")
        if relevance >= 80:
            reasons.append(f"high topical relevance ({relevance}%)")
        if entities:
            ent_names = ", ".join(e.name for e in entities[:3])
            reasons.append(f"mentions notable entities: {ent_names}")
        explanation = f"{importance} importance because: {'; '.join(reasons) if reasons else 'general content analysis'}."

        return ClassificationResult(
            category=category,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            relevance=relevance,
            importance=importance,
            importance_score=importance_score,
            should_index=relevance >= 30,
            should_alert=should_alert,
            is_significant_event=is_significant,
            explanation=explanation,
            entities=entities,
            raw_output={
                "category_scores": {k: v for k, v in scores.items() if v > 0},
                "positive_signals": pos,
                "negative_signals": neg,
                "breaking_detected": has_breaking,
            },
        )

    async def get_categories(self) -> List[str]:
        return list(self._categories)

    async def set_categories(self, categories: List[str]) -> None:
        self._categories = list(categories)


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK EMBEDDING PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class MockEmbeddingProvider(EmbeddingProvider):
    """
    Generates deterministic‑ish embeddings from text.
    Uses a hash‑seeded random vector so similar texts get *somewhat* similar
    vectors (not as good as a real model, but enough for demo RAG).
    """

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    async def embed(self, text: str) -> np.ndarray:
        # Base vector with slight noise
        base = np.zeros(self._dim, dtype=np.float32)

        # Word-level random indexing projections
        words = [re.sub(r"[^\w\s]", "", w) for w in text.lower().split()]
        words = [w for w in words if len(w) > 2]
        
        # Stop words to downweight common noise
        stop_words = {"the", "and", "for", "that", "this", "with", "are", "from", "have", "has", "was", "were", "what", "which"}
        
        for w in words:
            weight = 0.2 if w in stop_words else 1.0
            w_seed = int(hashlib.md5(w.encode()).hexdigest()[:8], 16)
            w_rng = np.random.RandomState(w_seed)
            base += w_rng.randn(self._dim).astype(np.float32) * weight

        # Add bigram signals
        if len(words) >= 2:
            for i in range(len(words) - 1):
                bigram = f"{words[i]}_{words[i+1]}"
                bg_seed = int(hashlib.md5(bigram.encode()).hexdigest()[:8], 16)
                bg_rng = np.random.RandomState(bg_seed)
                base += bg_rng.randn(self._dim).astype(np.float32) * 1.5

        norm = np.linalg.norm(base)
        if norm > 0:
            base /= norm
        return base

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        return [await self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "mock-embedding-384"


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK VECTOR STORE
# ═══════════════════════════════════════════════════════════════════════════
class MockVectorStore(VectorStore):
    """In‑memory vector store with cosine‑similarity search."""

    def __init__(self) -> None:
        self._vectors: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    async def add(self, embedding_id: str, vector: np.ndarray, metadata: Dict[str, Any]) -> None:
        self._vectors[embedding_id] = vector
        self._metadata[embedding_id] = metadata

    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        if not self._vectors:
            return []

        results: List[Tuple[str, float, Dict[str, Any]]] = []
        qn = np.linalg.norm(query_vector)
        if qn == 0:
            return []
        q_normed = query_vector / qn

        for eid, vec in self._vectors.items():
            meta = self._metadata[eid]
            # Apply filters
            if filter_metadata:
                skip = False
                for k, v in filter_metadata.items():
                    if k == "min_timestamp" and "timestamp" in meta:
                        if meta["timestamp"] < v:
                            skip = True
                            break
                    elif k in meta and meta[k] != v:
                        skip = True
                        break
                if skip:
                    continue

            vn = np.linalg.norm(vec)
            if vn == 0:
                continue
            score = float(np.dot(q_normed, vec / vn))
            results.append((eid, score, meta))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def delete(self, embedding_id: str) -> None:
        self._vectors.pop(embedding_id, None)
        self._metadata.pop(embedding_id, None)

    async def count(self) -> int:
        return len(self._vectors)


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK LLM PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class MockLLMProvider(LLMProvider):
    """
    Generates RAG answers using templates and the retrieved context.
    Does NOT invent information — only synthesises what's in the context.
    """

    async def generate(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> str:
        if not context.strip():
            return "I don't have enough information from the current feed to answer that question. Try asking about a topic that has been discussed recently."

        # Parse the context to extract post summaries
        posts = context.strip().split("\n---\n")
        post_count = len(posts)

        # Determine the topic from the prompt
        prompt_lower = prompt.lower()
        topic = "the discussed topics"
        for t in ["ai", "machine learning", "technology", "startups", "finance", "cybersecurity", "climate", "science", "gaming", "politics", "sports"]:
            if t in prompt_lower:
                topic = t.upper() if len(t) <= 3 else t.title()
                break

        # Check for time-related queries
        time_context = ""
        if any(w in prompt_lower for w in ["today", "last hour", "recent", "currently", "now", "trending"]):
            time_context = "Based on the most recent posts in the feed, "
        elif "yesterday" in prompt_lower:
            time_context = "Looking at yesterday's posts, "
        elif "compare" in prompt_lower:
            time_context = "Comparing the available data, "

        # Build summary from actual context
        key_points = []
        for p in posts[:5]:
            lines = p.strip().split("\n")
            for line in lines:
                if line.startswith("Text:"):
                    text = line[5:].strip()
                    # Truncate long texts
                    if len(text) > 120:
                        text = text[:120] + "..."
                    key_points.append(f"• {text}")
                    break

        summary_points = "\n".join(key_points) if key_points else "No specific details available."

        answer = f"""{time_context}here is a summary of {topic} activity based on {post_count} relevant posts from the feed:

**Key Developments:**

{summary_points}

**Analysis:**
The feed shows {"significant" if post_count > 3 else "some"} activity around {topic}. {"Multiple sources are reporting on related developments, suggesting this is a major trend." if post_count > 3 else "This topic has moderate coverage in the current feed."}

*This summary is generated from {post_count} source posts retrieved from the LayaPulse feed. All information is grounded in the available data.*"""

        # Simulate processing delay
        await asyncio.sleep(random.uniform(0.3, 0.8))
        return answer

    @property
    def model_name(self) -> str:
        return "mock-llm-v1"
