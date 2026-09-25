#!/usr/bin/env python3
"""
Standalone Verification Script for Resilient API Key Rotation Engine.

Usage:
    python3 source_code/scripts/test_key_rotation.py --keys "AIzaSyFake1,AIzaSyFake2,AIzaSyFake3"
    python3 scripts/test_key_rotation.py --keys "AIzaSyFake1,AIzaSyFake2,AIzaSyFake3"
"""
import argparse
import asyncio
import concurrent.futures
import io
import logging
import os
import sys
import time
from typing import List
from unittest.mock import AsyncMock, patch

# Ensure backend root is on sys.path
FILE_REALPATH = os.path.realpath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(FILE_REALPATH))
for candidate in [
    os.path.join(PROJECT_ROOT, "source", "backend"),
    os.path.join(PROJECT_ROOT, "source_code", "backend"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"),
]:
    abs_cand = os.path.abspath(candidate)
    if os.path.isdir(abs_cand) and abs_cand not in sys.path:
        sys.path.insert(0, abs_cand)

# Fallback: if dependencies like httpx are inside local venv, resolve site-packages
try:
    import httpx
except ImportError:
    import glob
    for pat in [
        "/home/felixsu/.gemini/antigravity-ide/scratch/koshi/backend/venv/lib/python*/site-packages",
        os.path.expanduser("~/.gemini/antigravity-ide/scratch/koshi/backend/venv/lib/python*/site-packages"),
        os.path.join(PROJECT_ROOT, "source", "backend", "venv", "lib", "python*", "site-packages"),
        os.path.join(PROJECT_ROOT, "source", "backend", ".venv", "lib", "python*", "site-packages"),
    ]:
        for p in glob.glob(pat):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)

from app.services.key_rotator import (
    KeyRotator,
    AllKeysExhaustedException,
    NoKeysConfiguredException,
    mask_key,
)
from app.services.ai_service import AIService, AIFeature, AITier


class TestRunner:
    def __init__(self, raw_keys: str, default_cooldown: float = 2.0, verbose: bool = False):
        self.raw_keys = raw_keys
        self.keys: List[str] = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.default_cooldown = default_cooldown
        self.verbose = verbose
        self.passed = 0
        self.failed = 0

    def log(self, msg: str, status: str = "INFO"):
        prefix = {
            "INFO": "\033[94m[*]\033[0m",
            "PASS": "\033[92m[✓]\033[0m",
            "FAIL": "\033[91m[✗]\033[0m",
            "WARN": "\033[93m[!]\033[0m",
        }.get(status, "[*]")
        print(f"{prefix} {msg}")

    def assert_true(self, condition: bool, description: str):
        if condition:
            self.passed += 1
            self.log(description, status="PASS")
        else:
            self.failed += 1
            self.log(f"FAILED: {description}", status="FAIL")

    def run_all(self):
        print("\n" + "=" * 70)
        print("  KOSHI AI KEY ROTATION VERIFICATION SUITE")
        print(f"  Configured Keys : {', '.join(mask_key(k) for k in self.keys)}")
        print(f"  Default Cooldown: {self.default_cooldown}s")
        print("=" * 70 + "\n")

        self.test_round_robin()
        self.test_concurrency_thread_safety()
        self.test_error_triggered_rotation_and_cooldown()
        self.test_secret_masking()
        self.test_all_keys_exhausted_cascade()
        self.test_cooldown_expiration_recovery()
        self.test_ai_service_integration_retry()

        print("\n" + "=" * 70)
        if self.failed == 0:
            print(f"\033[92m  ALL TESTS PASSED: {self.passed} passed, 0 failed\033[0m")
            print("=" * 70 + "\n")
            return 0
        else:
            print(f"\033[91m  TESTS FAILED: {self.failed} failed, {self.passed} passed\033[0m")
            print("=" * 70 + "\n")
            return 1

    def test_round_robin(self):
        print("--- Test 1: Round-Robin Key Dispatch ---")
        rotator = KeyRotator(keys=self.keys)
        self.assert_true(rotator.total_keys == len(self.keys), f"Rotator registered {len(self.keys)} keys")

        # First cycle
        observed = [rotator.get_key() for _ in range(len(self.keys))]
        self.assert_true(observed == self.keys, f"First pass cycled exactly in order: {[mask_key(k) for k in observed]}")

        # Second cycle
        observed_2 = [rotator.get_key() for _ in range(len(self.keys))]
        self.assert_true(observed_2 == self.keys, f"Second pass repeated round-robin cycle without disruption")

    def test_concurrency_thread_safety(self):
        print("\n--- Test 2: Concurrency & Thread-Safety (Atomic Dispatch) ---")
        rotator = KeyRotator(keys=self.keys)
        num_workers = 12
        requests_per_worker = 100
        total_requests = num_workers * requests_per_worker  # 1200 is divisible by 2, 3, 4, 5, 6

        dispatched = []

        def worker():
            local_keys = []
            for _ in range(requests_per_worker):
                local_keys.append(rotator.get_key())
            return local_keys

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker) for _ in range(num_workers)]
            for fut in futures:
                dispatched.extend(fut.result())

        self.assert_true(len(dispatched) == total_requests, f"Dispatched {len(dispatched)}/{total_requests} requests under concurrency")

        # Distribution balance check
        counts = [dispatched.count(k) for k in self.keys]
        spread = max(counts) - min(counts)
        expected_per_key = total_requests // len(self.keys)
        self.assert_true(
            spread <= (total_requests % len(self.keys)),
            f"Atomic round-robin perfectly distributed: counts={counts} (target ~{expected_per_key} calls/key) across {num_workers} threads",
        )

    def test_error_triggered_rotation_and_cooldown(self):
        print("\n--- Test 3: Error-Triggered Rotation & Cooldown Isolation (HTTP 429) ---")
        rotator = KeyRotator(keys=self.keys, default_cooldown=self.default_cooldown)
        first_key = self.keys[0]
        second_key = self.keys[1] if len(self.keys) > 1 else self.keys[0]

        # Simulate 429 on first_key
        rotator.mark_exhausted(first_key, cooldown_seconds=self.default_cooldown)

        # Status check
        status = rotator.get_status()
        first_status = next(s for s in status["keys"] if s["key_masked"] == mask_key(first_key))
        self.assert_true(first_status["exhausted"] is True, f"Key {mask_key(first_key)} is isolated in cooldown")
        self.assert_true(
            first_status["cooldown_remaining_seconds"] > 0,
            f"Cooldown remaining recorded: {first_status['cooldown_remaining_seconds']}s",
        )

        # Next dispatch should seamlessly skip first_key
        next_key = rotator.get_key()
        self.assert_true(next_key != first_key, f"Rotator skipped exhausted key and yielded healthy key {mask_key(next_key)}")
        if len(self.keys) > 1:
            self.assert_true(next_key == second_key, f"Rotator selected next active key in round-robin sequence")

    def test_secret_masking(self):
        print("\n--- Test 4: Secret Token Masking (No Leak Guarantee) ---")
        test_key = "AIzaSyFakeSecretToken12345678"
        masked = mask_key(test_key)
        self.assert_true("..." in masked, f"Mask pattern contains ellipsis: {masked}")
        self.assert_true(not test_key in masked, f"Full key is NOT present in masked string")
        self.assert_true(masked.startswith("AIza") and masked.endswith("5678"), f"Mask preserves prefix & suffix for recognition: {masked}")

        # Check logger stream does not leak
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        rot_logger = logging.getLogger("app.services.key_rotator")
        rot_logger.addHandler(handler)
        rot_logger.setLevel(logging.INFO)

        rot = KeyRotator([test_key])
        rot.mark_exhausted(test_key, cooldown_seconds=5)
        log_output = log_stream.getvalue()
        rot_logger.removeHandler(handler)

        self.assert_true(test_key not in log_output, f"Raw secret token never leaked to logs")
        self.assert_true(masked in log_output, f"Masked key safely reported in logs: {masked}")

    def test_all_keys_exhausted_cascade(self):
        print("\n--- Test 5: All Keys Exhausted Fast-Fallback ---")
        rotator = KeyRotator(keys=self.keys, default_cooldown=self.default_cooldown)
        for k in self.keys:
            rotator.mark_exhausted(k, cooldown_seconds=self.default_cooldown)

        exhausted_raised = False
        try:
            rotator.get_key()
        except AllKeysExhaustedException as exc:
            exhausted_raised = True
            self.assert_true(
                "exhausted" in str(exc).lower(),
                f"AllKeysExhaustedException raised with diagnostic message: '{exc}'",
            )
        self.assert_true(exhausted_raised, "AllKeysExhaustedException immediately signals cascade fallback")

    def test_cooldown_expiration_recovery(self):
        print("\n--- Test 6: Cooldown Expiry & Recovery ---")
        short_cooldown = 0.3
        rotator = KeyRotator(keys=self.keys, default_cooldown=short_cooldown)
        target_key = self.keys[0]

        rotator.mark_exhausted(target_key, cooldown_seconds=short_cooldown)
        status_before = rotator.get_status()
        self.assert_true(status_before["healthy_keys"] == len(self.keys) - 1, f"Healthy keys reduced during cooldown ({status_before['healthy_keys']})")

        # Sleep past cooldown
        time.sleep(short_cooldown + 0.1)

        # After cooldown, key is unblocked
        recovered_key = None
        for _ in range(len(self.keys)):
            k = rotator.get_key()
            if k == target_key:
                recovered_key = k
                break
        self.assert_true(recovered_key == target_key, f"Key {mask_key(target_key)} automatically recovered after cooldown expired")

    def test_ai_service_integration_retry(self):
        print("\n--- Test 7: AIService Tier 1 Integration & Retry on 429 ---")
        custom_rotator = KeyRotator(keys=self.keys, default_cooldown=self.default_cooldown)
        AIService.set_rotator(custom_rotator)

        # Scenario A: First call hits 429, retry hits 200
        call_count = 0
        keys_used = []

        class MockResponse:
            def __init__(self, status_code: int, json_data: dict, text: str = ""):
                self.status_code = status_code
                self._json_data = json_data
                self.text = text

            def json(self):
                return self._json_data

        async def mock_post(url, headers=None, json=None):
            nonlocal call_count, keys_used
            call_count += 1
            auth_header = headers.get("Authorization", "")
            key = auth_header.replace("Bearer ", "")
            keys_used.append(key)

            if call_count == 1:
                # First attempt: HTTP 429 Rate Limit
                return MockResponse(
                    429,
                    {"error": {"message": "Rate limit exceeded", "code": "RESOURCE_EXHAUSTED"}},
                    text="RESOURCE_EXHAUSTED",
                )
            # Second attempt (rotated key): HTTP 200 Success
            return MockResponse(
                200,
                {"choices": [{"message": {"content": "Verified weekly summary from rotated key."}}]},
            )

        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post)):
            text, tier = asyncio.run(AIService._call_llm(
                AIFeature.WEEKLY_SUMMARY,
                "System instructions",
                "User prompt context",
            ))

            self.assert_true(tier == AITier.CLOUD, f"Tier 1 succeeded on retry: tier={tier.value}")
            self.assert_true(call_count == 2, f"Attempted initial call + 1 retry on 429 (call_count={call_count})")
            if len(self.keys) >= 2:
                self.assert_true(keys_used[0] != keys_used[1], f"Switched key on retry: {mask_key(keys_used[0])} -> {mask_key(keys_used[1])}")
                self.assert_true(
                    self.keys[0] in custom_rotator._exhausted_until,
                    f"First key {mask_key(self.keys[0])} placed into cooldown",
                )

        # Scenario B: All keys fail 429 -> graceful cascade to Tier 2 / Tier 3
        custom_rotator.reset_exhausted()
        async def mock_post_all_429(url, headers=None, json=None):
            return MockResponse(429, {"error": "Quota exceeded"}, text="quota limit exceeded")

        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post_all_429)):
            text, tier = asyncio.run(AIService._call_llm(
                AIFeature.WEEKLY_SUMMARY,
                "System instructions",
                "User prompt context",
            ))
            self.assert_true(
                tier in (AITier.OLLAMA, AITier.DETERMINISTIC),
                f"Clean cascade to secondary tier when cloud exhausted: tier={tier.value}",
            )
            self.assert_true(bool(text), "Produced valid response content during cascade fallback")


def main():
    parser = argparse.ArgumentParser(description="Verify AI API Key Rotation Engine")
    parser.add_argument(
        "--keys",
        type=str,
        default="",
        help="Comma-separated API keys (e.g. 'AIzaSyFake1,AIzaSyFake2,AIzaSyFake3')",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=2.0,
        help="Cooldown duration in seconds for testing (default: 2.0s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging output",
    )
    args = parser.parse_args()

    # Determine keys from argument or env
    keys_input = args.keys.strip()
    if not keys_input:
        keys_input = (
            os.getenv("GEMINI_API_KEYS")
            or os.getenv("AI_API_KEYS")
            or os.getenv("AI_API_KEY")
            or "AIzaSyFake1,AIzaSyFake2,AIzaSyFake3"
        )

    runner = TestRunner(raw_keys=keys_input, default_cooldown=args.cooldown, verbose=args.verbose)
    exit_code = runner.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
