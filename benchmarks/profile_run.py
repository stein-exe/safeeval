"""Quick cProfile run to identify bottlenecks."""

import cProfile
import pstats

from benchmarks.benchmark import _generate, _cross_check
from safeeval import evaluate

exprs = _generate(1000)

# Warm up
for e in exprs[:100]:
    try:
        evaluate(e)
    except Exception:
        pass

pr = cProfile.Profile()
pr.enable()
for e in exprs:
    try:
        evaluate(e)
    except Exception:
        pass
pr.disable()

stats = pstats.Stats(pr).sort_stats("cumulative")
stats.print_stats(25)
