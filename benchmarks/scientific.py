"""Measure complete evaluations with a warm cache; no timing assertions."""

import argparse
import json
import platform
import statistics
import time

import sympy

from mathechan import evaluate

BASELINE = {
    "arithmetic": "1/3+1/6",
    "derivative": "D[Sin[x^2],x]",
    "expand": "Expand[(x+y+z)^8]",
    "simplify": "Simplify[Sin[x]^2+Cos[x]^2]",
    "gaussian_plot": "Plot[Exp[-x^2],{x,-3,3}]",
    "rational_plot": "Plot[1/x,{x,1,2}]",
}
SCIENTIFIC = {
    "numerical": "N[Pi,50]",
    "factor": "Factor[x^8-1]",
    "together": "Together[1/x+1/(x+1)]",
    "cancel": "Cancel[(x^2-1)/(x-1)]",
    "substitute": "Substitute[Exp[-a*x],a,2]",
    "sum": "Sum[n^2,{n,1,1000}]",
    "integrate": "Integrate[Exp[-x^2],{x,-Infinity,Infinity}]",
    "solve": "Solve[x^2==2,x]",
    "ode": "DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]",
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("baseline", "all"), default="all")
    parser.add_argument("--repeats", type=int, default=9)
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 1000:
        parser.error("repeats must be between 1 and 1000")
    cases = BASELINE if args.suite == "baseline" else {**BASELINE, **SCIENTIFIC}
    measurements = {}
    for name, source in cases.items():
        evaluate(source)
        samples = []
        for _ in range(args.repeats):
            start = time.perf_counter()
            evaluate(source)
            samples.append((time.perf_counter() - start) * 1000)
        median = statistics.median(samples)
        measurements[name] = {
            "source": source,
            "median_ms": median,
            "mad_ms": statistics.median(abs(sample - median) for sample in samples),
            "samples_ms": samples,
        }
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "sympy": sympy.__version__,
                "platform": platform.platform(),
                "processor": platform.processor(),
                "cache": "warm; one warm-up per case; full evaluate including formatting",
                "repeats": args.repeats,
                "cases": measurements,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
