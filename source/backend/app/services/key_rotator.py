"""
Resilient, thread-safe API key rotation engine for AI cascade service.

Provides round-robin dispatch using itertools.cycle with thread-locking,
cooldown isolation upon HTTP 429 / quota errors, and safe masked logging.
"""
import itertools
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def mask_key(key: str) -> str:
    """
    Mask an API key for safe logging (e.g. AIza...1234).
    Guarantees no secret leakage in logs or stdout.
    """
    if not key:
        return "<empty>"
    clean = key.strip()
    if len(clean) <= 8:
        if len(clean) <= 4:
            return "***"
        return f"{clean[:2]}...{clean[-2:]}"
    return f"{clean[:4]}...{clean[-4:]}"


class KeyRotatorException(Exception):
    """Base exception for KeyRotator errors."""
    pass


class NoKeysConfiguredException(KeyRotatorException):
    """Raised when no API keys are available or configured."""
    pass


class AllKeysExhaustedException(KeyRotatorException):
    """Raised when all configured API keys are in cooldown/exhausted."""
    pass


class KeyRotator:
    """
    Thread-safe API Key Rotator supporting round-robin selection,
    exponential/configurable cooldown on quota exhaustion (HTTP 429/403),
    and fast fallback cascade when all keys are exhausted.
    """

    def __init__(
        self,
        keys: Optional[Union[List[str], str]] = None,
        default_cooldown: float = 60.0,
        env_var_names: Optional[List[str]] = None,
    ):
        self._lock = threading.Lock()
        self._default_cooldown = float(default_cooldown)
        self._env_var_names = env_var_names or [
            "GEMINI_API_KEYS",
            "AI_API_KEYS",
            "GEMINI_API_KEY",
            "AI_API_KEY",
        ]
        self._exhausted_until: Dict[str, float] = {}

        resolved_keys: List[str] = []
        if keys is not None:
            if isinstance(keys, str):
                resolved_keys = [k.strip() for k in keys.split(",") if k.strip()]
            else:
                resolved_keys = [k.strip() for k in keys if isinstance(k, str) and k.strip()]
        else:
            for env_var in self._env_var_names:
                val = os.getenv(env_var, "").strip()
                if val:
                    resolved_keys = [k.strip() for k in val.split(",") if k.strip()]
                    if resolved_keys:
                        break

        # Deduplicate while preserving round-robin insertion order
        seen = set()
        self._keys: List[str] = []
        for k in resolved_keys:
            if k not in seen:
                seen.add(k)
                self._keys.append(k)

        self._cycle = itertools.cycle(self._keys) if self._keys else None
        if self._keys:
            logger.info(
                "KeyRotator initialized with %d keys: [%s]",
                len(self._keys),
                ", ".join(mask_key(k) for k in self._keys),
            )
        else:
            logger.debug("KeyRotator initialized with 0 keys.")

    @property
    def total_keys(self) -> int:
        with self._lock:
            return len(self._keys)

    def has_keys(self) -> bool:
        with self._lock:
            return bool(self._keys)

    def available_keys_count(self) -> int:
        """Count how many keys are currently available (not in cooldown)."""
        with self._lock:
            now = time.monotonic()
            return sum(
                1
                for k in self._keys
                if k not in self._exhausted_until or self._exhausted_until[k] <= now
            )

    def get_key(self) -> str:
        """
        Thread-safe round-robin dispatch using itertools.cycle under lock.
        Skips keys currently in cooldown.
        Raises NoKeysConfiguredException if no keys exist.
        Raises AllKeysExhaustedException if all keys are currently in cooldown.
        """
        with self._lock:
            if not self._keys or self._cycle is None:
                raise NoKeysConfiguredException("No API keys configured in KeyRotator.")

            now = time.monotonic()
            total = len(self._keys)
            min_remaining: Optional[float] = None

            # Clean up expired cooldowns
            expired = [k for k, exp in self._exhausted_until.items() if exp <= now]
            for k in expired:
                del self._exhausted_until[k]

            # Inspect up to total keys in round-robin order
            for _ in range(total):
                candidate = next(self._cycle)
                exp = self._exhausted_until.get(candidate)
                if exp is None:
                    return candidate
                remaining = exp - now
                if min_remaining is None or remaining < min_remaining:
                    min_remaining = remaining

            # All keys are exhausted
            remaining_str = f"{min_remaining:.1f}s" if min_remaining is not None else "unknown"
            raise AllKeysExhaustedException(
                f"All {total} API keys are exhausted. Next key available in {remaining_str}."
            )

    def mark_exhausted(self, key: str, cooldown_seconds: Optional[float] = None) -> None:
        """
        Mark a key as exhausted (HTTP 429/quota limit) with cooldown duration.
        """
        cd = float(cooldown_seconds if cooldown_seconds is not None else self._default_cooldown)
        with self._lock:
            target_key = key.strip()
            if target_key not in self._keys:
                self._keys.append(target_key)
                self._cycle = itertools.cycle(self._keys)

            now = time.monotonic()
            self._exhausted_until[target_key] = now + cd
            masked = mask_key(target_key)
            logger.warning(
                "API key %s marked EXHAUSTED for %.1fs (cooldown until +%.1fs)",
                masked, cd, cd,
            )

    def reset_exhausted(self, key: Optional[str] = None) -> None:
        """Reset cooldown for a specific key or all keys."""
        with self._lock:
            if key:
                self._exhausted_until.pop(key.strip(), None)
            else:
                self._exhausted_until.clear()

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of all managed keys."""
        with self._lock:
            now = time.monotonic()
            status_list = []
            for k in self._keys:
                exp = self._exhausted_until.get(k)
                is_exhausted = exp is not None and exp > now
                remaining = max(0.0, exp - now) if is_exhausted else 0.0
                status_list.append({
                    "key_masked": mask_key(k),
                    "exhausted": is_exhausted,
                    "cooldown_remaining_seconds": round(remaining, 1),
                })
            return {
                "total_keys": len(self._keys),
                "healthy_keys": sum(1 for s in status_list if not s["exhausted"]),
                "keys": status_list,
            }
