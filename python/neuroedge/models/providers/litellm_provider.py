"""
`LiteLLMProvider` — System 2 through LiteLLM, used as a library (Q-10).

LiteLLM is the SDK only: never its proxy server, never imported by the core.
It comes with the extra ``pip install 'neuroedge[cloud]'`` (``litellm==1.102.0``,
Q-11) and is imported on the first call, so an agent without `[system_two]`
never pays for it.

Every failure raises `ProviderUnavailable` saying what to do, so the session
says its offline line (fail-safe, Q-14). Before any network call: the extra
must be installed and the key's environment variable set — otherwise nothing
is sent. The key is passed to LiteLLM per call and masked out of every error.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

from .base import ProviderUnavailable, scrub
from .config import SystemTwoConfig
from .openai_chat import from_response, to_messages, tools_of, usage_of

INSTALL = "pip install 'neuroedge[cloud]'"
# LiteLLM fetches its model price map from GitHub on import unless told not to;
# the map bundled in the wheel is enough, and an import must not touch the network.
_LOCAL_COST_MAP = "LITELLM_LOCAL_MODEL_COST_MAP"
GRACE = 1.25  # the whole call may take timeout_s × GRACE before it is abandoned


def _import_litellm() -> Any:
    os.environ.setdefault(_LOCAL_COST_MAP, "True")
    import litellm

    litellm.suppress_debug_info = True  # no "Give Feedback" banner on stdout
    return litellm


def _failure(exc: BaseException) -> tuple[str, str]:
    """(why, how) for a LiteLLM / OpenAI SDK exception, from its class name only."""
    kind = type(exc).__name__
    if "Timeout" in kind:
        return "the model did not answer in time", "try again, or raise timeout_s in [system_two]"
    if kind in ("AuthenticationError", "PermissionDeniedError"):
        return "the provider rejected the API key", "check the key in the api_key_env variable"
    if kind == "RateLimitError":
        return "the provider is rate limiting this key", "wait, or check the plan's quota"
    if kind == "NotFoundError":
        return "the provider does not know this model", "check `model` in [system_two]"
    if kind in ("APIConnectionError", "ServiceUnavailableError", "InternalServerError"):
        return "the provider could not be reached", "check the network and api_base"
    return "the provider returned an error", "check the model name and the provider's status"


class LiteLLMProvider:
    """A `SystemTwo` provider: ``await provider(task, name, state)``."""

    name = "litellm"

    def __init__(
        self,
        config: SystemTwoConfig,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.config = config
        self.model = config.model
        self.environ = os.environ if environ is None else environ
        self.last_usage: dict[str, Any] | None = None
        self._litellm: Any = None

    @property
    def where(self) -> str:
        return f"SystemTwo(litellm:{self.model})"

    def _library(self) -> Any:
        if self._litellm is None:
            try:
                self._litellm = _import_litellm()
            except ImportError as exc:
                raise ProviderUnavailable(
                    where=self.where,
                    why=f"LiteLLM is not installed — {INSTALL}",
                    how=f"{INSTALL} (the `cloud` extra, Q-10)",
                    called=False,
                ) from exc
        return self._litellm

    def _key(self) -> str | None:
        name = self.config.api_key_env
        if name is None:
            return None  # a keyless local server (api_base)
        key = self.environ.get(name, "")
        if not key.strip():
            raise ProviderUnavailable(
                where=self.where,
                why=f"{name} is not set — set {name} to the API key (nothing was sent)",
                how=f"export {name}=<your key>, or remove [system_two] to stay offline",
                called=False,
            )
        return key

    def _request(self, task: str, name: str | None, state: Mapping[str, Any] | None, key):
        request: dict[str, Any] = {
            "model": self.model,
            "messages": to_messages(task, name, state),
            "timeout": self.config.timeout_s,
        }
        if task == "respond":
            tools = tools_of(state)
            if tools:
                request["tools"] = tools
        if key is not None:
            request["api_key"] = key
        for field in ("api_base", "max_tokens", "temperature"):
            value = getattr(self.config, field)
            if value is not None:
                request[field] = value
        return request

    async def __call__(self, task: str, name: str | None, state: Mapping[str, Any] | None) -> Any:
        self.last_usage = None
        litellm = self._library()
        key = self._key()
        request = self._request(task, name, state, key)
        try:
            # LiteLLM applies `timeout` per attempt; this bounds the whole call, retries included.
            response = await asyncio.wait_for(
                litellm.acompletion(**request), timeout=self.config.timeout_s * GRACE
            )
        except TimeoutError:
            how = "try again, or raise timeout_s in [system_two]"
            raise ProviderUnavailable(
                where=self.where,
                why=f"the model did not answer within {self.config.timeout_s:g} s — {how}",
                how=how,
            ) from None
        except Exception as exc:
            # `why` is what the trace records (`system_two_unavailable.reason`), so it
            # says what to do too. The original is not chained: it may carry the request.
            why, how = _failure(exc)
            detail = scrub(f"{type(exc).__name__}: {exc}", key)[:200]
            raise ProviderUnavailable(
                where=self.where, why=f"{why} — {how} ({detail})", how=how
            ) from None
        self.last_usage = {**usage_of(response), **self._cost(litellm, response)}
        reply = from_response(response, where=self.where)
        if task == "respond":
            return reply
        if not reply["text"]:
            raise ProviderUnavailable(
                where=self.where,
                why="the model answered with no text — try again; check max_tokens",
                how="try again; check max_tokens in [system_two]",
            )
        return reply["text"]

    @staticmethod
    def _cost(litellm: Any, response: Any) -> dict[str, Any]:
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:  # unknown price: the call still counts, without a cost
            return {}
        if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
            return {"cost_usd": round(float(cost), 8)}
        return {}
