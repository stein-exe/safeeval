# safeeval

A small, dependency-free Python library that safely evaluates arithmetic
expressions **without** using `eval`, `exec`, `ast.literal_eval`, or any
third-party parser.

## Supported operators

- Binary: `+`, `-`, `*`, `/`, `%`, `**`
- Unary:  `-`, `+`
- Parentheses: `(`, `)`

Precedence and associativity match Python's arithmetic rules.

## Usage

```python
from safeeval import evaluate

evaluate("1 + 2 * 3")          # 7.0
evaluate("(1 + 2) * 3")        # 9.0
evaluate("2 ** 3 ** 2")        # 512.0   (right-associative)
evaluate("-2 ** 2")            # -4.0    (unary binds looser than **)
evaluate("10 % 3")             # 1.0
evaluate("7 / 2")              # 3.5
```

## Errors

- `SyntaxError` is raised for any malformed expression
  (unmatched parens, trailing operator, etc.).
- `ZeroDivisionError` is raised on `/ 0` or `% 0`.

## Layout

- `safeeval/_tokenizer.py` — character-by-character scanner
- `safeeval/_parser.py` — Pratt (top-down operator precedence) parser
- `safeeval/_evaluator.py` — public `evaluate` entry point

## Tests and benchmarks

```
python -m pytest tests -q
python benchmarks/benchmark.py
```
