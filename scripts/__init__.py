"""Standalone exploration/reporting scripts (run directly via `python
scripts/foo.py`), not part of the installed `hoqi_bench` package. This
file exists only so `scripts.robustness_matrix` is importable from
`tests/test_robustness_matrix.py` and unambiguous to mypy -- see that
test's own note on why the matrix needs to be re-run by pytest, not just
read from a one-time script output."""
