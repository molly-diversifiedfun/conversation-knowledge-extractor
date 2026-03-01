"""Anthropic SDK wrapper with retry, backoff, and rate limiting."""

from __future__ import annotations

import logging
import time

import anthropic

from .models import ApiResponse

logger = logging.getLogger(__name__)


class ApiClient:
    """Thin wrapper around anthropic.Anthropic with retry and rate limiting."""

    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds, doubles each retry

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._last_call_time: float = 0.0

    def call(
        self,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        prompt: str,
        rate_limit_gap: float,
    ) -> ApiResponse:
        """Send a message to Claude with retry and rate limiting.

        Args:
            model: Model identifier (e.g. claude-haiku-4-5-20251001)
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            prompt: User message content
            rate_limit_gap: Minimum seconds between API calls

        Returns:
            ApiResponse with text and token counts

        Raises:
            anthropic.APIError: After all retries exhausted
        """
        self._wait_for_rate_limit(rate_limit_gap)

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                self._last_call_time = time.monotonic()
                return ApiResponse(
                    text=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    stop_reason=response.stop_reason,
                )
            except anthropic.RateLimitError as e:
                last_error = e
                delay = self.BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d), waiting %.1fs",
                    attempt + 1, self.MAX_RETRIES, delay,
                )
                time.sleep(delay)
            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    last_error = e
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Server error %d (attempt %d/%d), waiting %.1fs",
                        e.status_code, attempt + 1, self.MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
                else:
                    raise

        raise last_error  # type: ignore[misc]

    def _wait_for_rate_limit(self, gap: float) -> None:
        """Enforce minimum gap between API calls."""
        if self._last_call_time > 0:
            elapsed = time.monotonic() - self._last_call_time
            if elapsed < gap:
                time.sleep(gap - elapsed)
