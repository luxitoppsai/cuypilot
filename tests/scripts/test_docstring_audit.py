import json


def test_reports_missing_and_incomplete_docstrings(write, run_script, tmp_path):
    write(
        "pkg/mod.py",
        '''
        """Module doc."""

        def ok(a: int) -> int:
            """Fine.

            :param a: A.
            :returns: A.
            """
            return a

        def no_doc(x):
            return x

        def bad(a, b) -> int:
            """Bad.

            :param a: A.
            :param c: Not a param.
            """
            return a

        def gen(n):
            """Gen.

            :param n: N.
            """
            yield n

        def _private(x):
            return x

        class Thing:
            """A thing."""

            def __init__(self, size):
                self.size = size

            def run(self):
                """Run it."""
        ''',
    )
    findings = {
        f["name"]: f["problems"]
        for f in json.loads(run_script("sphinx-docstrings", "docstring_audit.py", str(tmp_path), "--json"))
    }

    assert "ok" not in findings and "_private" not in findings and "Thing.run" not in findings
    assert findings["no_doc"] == ["missing docstring"]
    assert findings["bad"] == ["missing :param: b", "documents unknown params c", "missing :returns:"]
    assert findings["gen"] == ["missing :yields:"]
    assert findings["Thing.__init__"] == ["missing :param: size"]


def test_text_output_and_skips_hidden_dirs(write, run_script, tmp_path):
    write(".venv/lib/x.py", "def f(): pass\n")
    write("m.py", '"""Doc."""\n\ndef f():\n    pass\n')
    out = run_script("sphinx-docstrings", "docstring_audit.py", str(tmp_path))
    assert "m.py:3  function  f - missing docstring" in out
    assert ".venv" not in out
    assert "1 element(s) to document in 1 file(s)." in out
