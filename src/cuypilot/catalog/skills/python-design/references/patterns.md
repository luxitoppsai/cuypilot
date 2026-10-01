# Design patterns: when (not) to use them in Python

Use a pattern only when the problem it solves exists **today**. Try the Pythonic alternative first.

| Pattern | Use when | Do not use when | Pythonic alternative first |
|---|---|---|---|
| Strategy | 2+ interchangeable algorithms chosen at runtime | Only one algorithm exists | Pass a function (`Callable`) or a dict `{name: func}` |
| Factory | Object creation depends on runtime data and is non-trivial | A constructor call is enough | A plain function or `@classmethod` alternate constructor (`from_config`) |
| Abstract Factory | Families of related objects that must vary together | Single product type | Usually never needed; use a module per family |
| Builder | Many optional parts with validation between steps | A few keyword arguments suffice | Keyword arguments with defaults, `dataclass` |
| Singleton | — (almost never) | Always prefer something else | A module-level object, or pass the instance explicitly |
| Adapter | Integrating an external API whose interface differs from what your code expects | You control both sides | A small wrapper function |
| Facade | Simplifying a complex subsystem behind a few calls used in many places | Only one caller | A module with a few public functions |
| Decorator (GoF) | Adding behavior to objects dynamically, stackable | Behavior is fixed | Python decorators on functions, `functools.wraps` |
| Observer | Several independent consumers react to events | One consumer | Pass a callback; a list of callbacks |
| Template Method | Fixed algorithm skeleton with varying steps across 2+ subclasses | One variant | Higher-order function receiving the varying steps |
| Repository | Isolating persistence so domain logic is testable | Simple scripts or notebooks | A module of read/write functions |
| Command | Queuing, undo/redo, or logging operations as objects | Direct calls suffice | Functions + `functools.partial` |
| State | Behavior changes substantially with an explicit state machine | 2–3 states with simple branching | `Enum` + `match`/dict dispatch |

## Python building blocks that replace most patterns

- First-class functions, closures, `functools.partial`.
- `dataclass(frozen=True)`, `NamedTuple`, `Enum`.
- `typing.Protocol` for structural interfaces.
- Modules as natural singletons and namespaces.
- Context managers (`with`) for resource lifetimes.
- Generators for streaming/pipelines.
