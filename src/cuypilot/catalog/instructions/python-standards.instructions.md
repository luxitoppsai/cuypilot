---
applyTo: "**/*.py"
description: "Team Python standards: KISS, YAGNI, pragmatic OOP, validate at the edges, Sphinx docstrings."
---

# Python standards

Apply these rules to every Python change. They are defaults; a project's own conventions win when they conflict.

## Simplicity
- Write the simplest code that solves the current requirement (KISS). Prefer the standard library and the platform before adding a dependency or a wrapper.
- Do not add flags, parameters, layers, base classes or extension points for hypothetical future needs (YAGNI). Add them when a second real use case appears.
- Prefer deleting code over adding code. Remove dead code, unused parameters and commented-out blocks you touch.

## Functions vs classes
- Use plain functions for stateless logic and data transformations.
- Use a class only when it owns state plus the behavior that operates on it, when you need polymorphism, or when it defines a clear boundary (e.g. a client, a repository).
- Use `@dataclass` (or `NamedTuple`) for data containers instead of hand-written classes or loose dicts.
- Prefer composition over inheritance. Avoid hierarchies deeper than one level unless the domain clearly demands it.
- Use `typing.Protocol` for interfaces instead of abstract base classes when duck typing is enough.

## Robustness at the edges
- Validate external input (user input, files, HTTP/API responses, environment variables) where it enters the system.
- Trust internal code and framework guarantees. Do not wrap everything in defensive `try/except`; catch only exceptions you can handle meaningfully, and never use bare `except:` or silently `pass`.
- Fail loudly with a specific exception and a clear message.

## Readability
- Clear, descriptive names; no unexplained abbreviations. Functions short and with one responsibility.
- Type hints on public functions and methods.
- Comments explain *why*, not *what*.

## Docstrings
- Public modules, classes and functions get a Sphinx (reST) docstring:

```python
def load_index(path: Path) -> Index:
    """Load the TF-IDF index from disk.

    :param path: Folder that contains ``vectorizer.pkl`` and ``matrix.pkl``.
    :returns: The index, ready to query.
    :raises FileNotFoundError: If the folder does not contain the index.
    """
```

## Tests
- Add tests where the cost of a bug justifies them (business logic, data transformations, parsing). Prefer `pytest` with plain functions and fixtures.
