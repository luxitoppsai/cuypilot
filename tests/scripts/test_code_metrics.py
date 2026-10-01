import json


def test_flags_complexity_overengineering_and_swallowed_errors(write, run_script, tmp_path):
    branches = "\n".join(f"    if x == {i}:\n        return {i}" for i in range(25))
    write("big.py", f"def tangled(x):\n{branches}\n    return -1\n")
    write(
        "design.py",
        """
        from abc import ABC, abstractmethod

        class Base(ABC):
            @abstractmethod
            def go(self): ...

        class Only(Base):
            def go(self):
                return 1

        class Wrapper:
            def __init__(self, x):
                self.x = x

            def compute(self):
                return self.x * 2

        def many(a, b, c, d, e, f, g):
            try:
                return a
            except Exception:
                pass

        def worse():
            try:
                pass
            except:
                return None
        """,
    )
    findings = json.loads(run_script("design-review", "code_metrics.py", str(tmp_path), "--json"))
    problems = [(f["severity"], f["name"], f["problem"].split(" ")[0]) for f in findings]

    assert ("HIGH", "tangled", "complexity=26") in problems
    assert ("MEDIUM", "tangled", "lines=52") in problems
    assert ("MEDIUM", "many", "params=7") in problems
    assert ("HIGH", "except", "exception") in problems
    assert ("HIGH", "except", "bare") in problems
    assert ("MEDIUM", "Base", "abstract") in problems
    assert ("LOW", "Wrapper", "class") in problems
    assert [f["severity"] for f in findings] == sorted(
        (f["severity"] for f in findings), key=["HIGH", "MEDIUM", "LOW"].index
    )


def test_limit(write, run_script, tmp_path):
    write(
        "m.py", "".join(f"def f{i}():\n    try:\n        pass\n    except:\n        pass\n" for i in range(5))
    )
    out = run_script("design-review", "code_metrics.py", str(tmp_path), "--limit", "2")
    assert "5 finding(s) in 1 file(s), 3 not shown." in out


def test_elif_chain_is_not_nesting(write, run_script, tmp_path):
    chain = "\n".join(f"    {'if' if i == 0 else 'elif'} x == {i}:\n        y = {i}" for i in range(6))
    write("m.py", f"def flat(x):\n{chain}\n    return x\n")
    findings = json.loads(run_script("design-review", "code_metrics.py", str(tmp_path), "--json"))
    assert not [f for f in findings if f["problem"].startswith("nesting")]
