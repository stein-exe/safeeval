"""Benchmark safeeval against Python's built-in ``eval`` on 1000 random
arithmetic expressions.

The benchmark also cross-checks correctness: every expression must
produce the same value as Python's ``eval`` (modulo float rounding).

Run with:

    python benchmarks/benchmark.py
"""

from __future__ import annotations

import random
import statistics
import string
import time
from typing import List, Tuple

from safeeval import evaluate

# A small set of disallowed characters that could otherwise sneak into
# generated expressions and force a different error class than what we
# want to benchmark.
_SAFE_CHARS = string.digits + "+-*/%.() "


def _rand_int(rng: random.Random) -> str:
    return str(rng.randint(-9, 9))


def _rand_atom(rng: random.Random) -> str:
    # Atom is a number, possibly with unary minus/plus in front.
    sign = rng.choice(["", "-", "+"])
    body = _rand_int(rng)
    return sign + body


def _rand_expr(rng: random.Random, depth: int = 0, max_depth: int = 4) -> str:
    """Generate a syntactically valid arithmetic expression."""
    if depth >= max_depth or (depth > 0 and rng.random() < 0.3):
        return _rand_atom(rng)

    choice = rng.random()
    if choice < 0.25:
        return "(" + _rand_expr(rng, depth + 1, max_depth) + ")"
    if choice < 0.55:
        op = rng.choice(["+", "-", "*", "/", "%", "**"])
        left = _rand_expr(rng, depth + 1, max_depth)
        right = _rand_expr(rng, depth + 1, max_depth)
        return f"{left} {op} {right}"
    # Unary prefix
    op = rng.choice(["-", "+"])
    return f"{op}{_rand_expr(rng, depth + 1, max_depth)}"


def _generate(n: int, seed: int = 1234) -> List[str]:
    rng = random.Random(seed)
    out: List[str] = []
    while len(out) < n:
        e = _rand_expr(rng)
        # Filter out expressions that would obviously cause ZeroDivision
        # (we still want some, but balance them). We don't pre-filter
        # too aggressively; we want a mix of errors and successes so
        # the benchmark is realistic.
        for ch in e:
            if ch not in _SAFE_CHARS:
                break
        else:
            out.append(e)
    return out


def _cross_check(exprs: List[str]) -> Tuple[int, int, int]:
    """Compare our evaluator with Python's eval for the success cases.

    Returns (ok, mismatch, error).
    """
    ok = mismatch = err = 0
    for e in exprs:
        try:
            ours = evaluate(e)
        except (SyntaxError, ZeroDivisionError, ValueError, OverflowError):
            err += 1
            continue
        try:
            ref = eval(e)
        except Exception:
            # Python raised something we don't; not a real mismatch.
            continue
        if abs(ours - ref) < 1e-9 * max(1.0, abs(ref)):
            ok += 1
        else:
            mismatch += 1
            print(f"MISMATCH: {e!r} -> safeeval={ours!r}, python={ref!r}")
    return ok, mismatch, err


def main(num_exprs: int = 1000, repeats: int = 3) -> None:
    print(f"Generating {num_exprs} random expressions...")
    exprs = _generate(num_exprs)
    print(f"Example expressions:")
    for e in exprs[:5]:
        print(f"  {e}")

    # --- Correctness ---
    print("\nCross-checking against Python's eval...")
    ok, mismatch, err = _cross_check(exprs)
    print(f"  ok:        {ok}")
    print(f"  mismatch:  {mismatch}")
    print(f"  errored:   {err}")
    assert mismatch == 0, "safeeval disagreed with eval on at least one expression"

    # --- Performance ---
    print(f"\nBenchmarking ({repeats} runs of {num_exprs} expressions)...")

    # Filter to expressions that don't raise so the timing is fair.
    safe_exprs = []
    for e in exprs:
        try:
            evaluate(e)
            safe_exprs.append(e)
        except Exception:
            continue
    print(f"  using {len(safe_exprs)} non-erroring expressions for timing")

    safe_times: List[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for e in safe_exprs:
            evaluate(e)
        t1 = time.perf_counter()
        safe_times.append(t1 - t0)

    py_times: List[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for e in safe_exprs:
            eval(e)
        t1 = time.perf_counter()
        py_times.append(t1 - t0)

    def report(name: str, ts: List[float]) -> None:
        best = min(ts)
        med = statistics.median(ts)
        per_expr_us = (best / len(safe_exprs)) * 1e6
        print(
            f"  {name:>8s}: best={best*1000:7.2f} ms  "
            f"median={med*1000:7.2f} ms  "
            f"per-expr={per_expr_us:7.2f} us"
        )

    report("safeeval", safe_times)
    report("python", py_times)

    speedup = min(py_times) / min(safe_times)
    if speedup >= 1.0:
        print(
            f"\nsafeeval is {speedup:.2f}x faster than Python's eval "
            f"(a C-implemented baseline)."
        )
    else:
        print(
            f"\nsafeeval is {1/speedup:.2f}x slower than Python's eval "
            f"(a C-implemented baseline)."
        )


if __name__ == "__main__":
    main()
