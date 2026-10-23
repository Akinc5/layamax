"""
Live X / Twitter API v2 Streaming Provider for LayaPulse.

Supports:
1. X API v2 Filtered Stream (real-time persistent SSE stream)
2. X API v2 Recent Search Polling (high-reliability endpoint compatible with Free/Basic/Pro tiers)
3. Auto-fallback and graceful rate-limit handling with exponential backoff
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Set

import httpx

from config import settings
from mock_providers import MockStreamProvider
from providers import StreamProvider
from schemas import RawPost

logger = logging.getLogger("layapulse.twitter")


class TwitterStreamProvider(StreamProvider):
    """
    Consumes live posts from X (Twitter) API v2 and yields RawPost objects.
    """

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        search_query: Optional[str] = None,
        stream_type: str = "auto",
        poll_interval: float = 8.0,
    ) -> None:
        self.bearer_token = bearer_token or settings.twitter_bearer_token
        self.search_query = search_query or settings.twitter_search_query
        self.stream_type = stream_type or settings.twitter_stream_type
        self.poll_interval = poll_interval or settings.twitter_poll_interval

        self._running = True
        self._seen_ids: Set[str] = set()
        self._mock_fallback = MockStreamProvider(interval=settings.mock_post_interval)

    @property
    def is_configured(self) -> bool:
        return bool(self.bearer_token and len(self.bearer_token.strip()) > 10)

    async def stream(self) -> AsyncIterator[RawPost]:
        """Continuously yield incoming live tweets from Twitter API v2."""
        if not self.is_configured:
            logger.warning(
                "⚠️  No valid TWITTER_BEARER_TOKEN found in .env. "
                "Running in simulated live mode. Add your Twitter Bearer Token to .env to switch to live X API data."
            )
            async for post in self._mock_fallback.stream():
                if not self._running:
                    break
                yield post
            return

        headers = {
            "Authorization": f"Bearer {self.bearer_token.strip()}",
            "User-Agent": "LayaPulse-Intelligence/1.0",
        }

        # Try filtered stream first if requested or auto
        if self.stream_type in ("filtered", "auto"):
            logger.info("Attempting to connect to X API v2 Filtered Stream...")
            try:
                async for post in self._stream_filtered(headers):
                    if not self._running:
                        break
                    yield post
                return
            except Exception as e:
                logger.warning("Filtered stream unavailable (%s). Falling back to Recent Search polling.", e)

        # Fallback to recent search polling
        logger.info("Streaming via X API v2 Recent Search Polling (query='%s')...", self.search_query)
        async for post in self._stream_polling(headers):
            if not self._running:
                break
            yield post

    async def _stream_filtered(self, headers: Dict[str, str]) -> AsyncIterator[RawPost]:
        """Consumes real-time streaming endpoint /2/tweets/search/stream."""
        url = "https://api.twitter.com/2/tweets/search/stream"
        params = {
            "expansions": "author_id",
            "tweet.fields": "created_at,public_metrics,entities,lang",
            "user.fields": "name,username,profile_image_url,verified",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)) as client:
            async with client.stream("GET", url, headers=headers, params=params) as response:
                if response.status_code == 403:
                    raise PermissionError("Filtered stream not permitted on this X API access tier (HTTP 403)")
                elif response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(f"X API stream failed: HTTP {response.status_code} - {body.decode(errors='ignore')}")

                logger.info("✅  Connected to X API v2 Filtered Stream successfully!")
                async for line in response.aiter_lines():
                    if not self._running:
                        break
                    if not line or not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        post = self._parse_tweet_payload(data)
                        if post and post.external_id not in self._seen_ids:
                            self._seen_ids.add(post.external_id)
                            if len(self._seen_ids) > 10000:
                                self._seen_ids.clear()
                            yield post
                    except Exception as err:
                        logger.debug("Skipping unparseable stream payload: %s", err)

    async def _stream_polling(self, headers: Dict[str, str]) -> AsyncIterator[RawPost]:
        """Polls /2/tweets/search/recent with since_id tracking for continuous ingestion."""
        url = "https://api.twitter.com/2/tweets/search/recent"
        since_id: Optional[str] = None
        consecutive_errors = 0

        async with httpx.AsyncClient(timeout=15.0) as client:
            while self._running:
                params = {
                    "query": self.search_query,
                    "max_results": 15,
                    "expansions": "author_id",
                    "tweet.fields": "created_at,public_metrics,entities,lang",
                    "user.fields": "name,username,profile_image_url,verified",
                }
                if since_id:
                    params["since_id"] = since_id

                try:
                    resp = await client.get(url, headers=headers, params=params)
                    if resp.status_code == 429:
                        reset_header = resp.headers.get("x-rate-limit-reset")
                        wait_sec = 60.0
                        if reset_header:
                            try:
                                wait_sec = max(5.0, float(reset_header) - datetime.utcnow().timestamp())
                            except Exception:
                                pass
                        logger.warning("X API rate limit (429) hit. Pausing for %.1fs...", min(wait_sec, 120.0))
                        await asyncio.sleep(min(wait_sec, 60.0))
                        continue

                    if resp.status_code != 200:
                        logger.error("X API search returned status %d: %s", resp.status_code, resp.text)
                        consecutive_errors += 1
                        backoff = min(60.0, 5.0 * (2 ** consecutive_errors))
                        await asyncio.sleep(backoff)
                        continue

                    consecutive_errors = 0
                    payload = resp.json()
                    tweets = payload.get("data", [])
                    users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}

                    if tweets:
                        # Tweets are returned latest first; update since_id to newest
                        newest_id = payload.get("meta", {}).get("newest_id") or tweets[0]["id"]
                        since_id = newest_id

                        # Yield chronologically (oldest to newest)
                        for tweet in reversed(tweets):
                            tweet_id = tweet["id"]
                            if tweet_id in self._seen_ids:
                                continue
                            self._seen_ids.add(tweet_id)
                            if len(self._seen_ids) > 10000:
                                self._seen_ids.clear()

                            author_id = tweet.get("author_id")
                            user = users.get(author_id, {})
                            post = self._build_raw_post(tweet, user)
                            yield post

                except Exception as ex:
                    logger.warning("Error fetching tweets from X API: %s", ex)
                    consecutive_errors += 1
                    await asyncio.sleep(5.0)

                await asyncio.sleep(self.poll_interval)

    def _parse_tweet_payload(self, data: Dict[str, Any]) -> Optional[RawPost]:
        """Parses a single stream response containing tweet and includes.users."""
        tweet = data.get("data")
        if not tweet:
            return None
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        user = users.get(tweet.get("author_id"), {})
        return self._build_raw_post(tweet, user)

    def _build_raw_post(self, tweet: Dict[str, Any], user: Dict[str, Any]) -> RawPost:
        """Converts Twitter API v2 objects to the unified RawPost schema."""
        tweet_id = tweet["id"]
        username = user.get("username", "twitter_user")
        name = user.get("name", username)
        avatar = user.get("profile_image_url", f"https://api.dicebear.com/7.x/initials/svg?seed={username}")

        # Parse timestamp
        created_at_str = tweet.get("created_at")
        if created_at_str:
            try:
                # Format: 2026-09-28T09:00:00.000Z
                ts = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                ts = datetime.utcnow()
        else:
            ts = datetime.utcnow()

        metrics = tweet.get("public_metrics", {})

        return RawPost(
            external_id=f"tw_{tweet_id}",
            author_name=name,
            author_username=username,
            author_avatar=avatar,
            text=tweet.get("text", ""),
            timestamp=ts,
            url=f"https://x.com/{username}/status/{tweet_id}",
            likes=metrics.get("like_count", 0),
            reposts=metrics.get("retweet_count", 0),
            replies=metrics.get("reply_count", 0),
            views=metrics.get("impression_count", 0),
            raw_data=tweet,
        )

    async def stop(self) -> None:
        """Stops the stream ingestion loop."""
        self._running = False
        await self._mock_fallback.stop()
