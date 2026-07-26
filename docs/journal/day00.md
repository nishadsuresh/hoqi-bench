# Day 0 — VS Code environment

## What got built

A committed `.vscode/` workspace configuration for `hoqi-bench`, plus the Python environment it depends on.

- **`.vscode/settings.json`** — points VS Code's Python extension at the project's virtual environment, turns on pytest as the test runner (looking in `tests/`), and sets Ruff as the formatter for Python files with format-on-save plus auto-fix and import-sorting on save. Also sets editor rulers at 88 and 100 columns (88 is Ruff's default line length; 100 is a soft "this is getting long" guide) and turns on mypy strict-mode type checking.
- **`.vscode/extensions.json`** — a recommendations list (Python, Pylance, Ruff, Jupyter, GitLens, Even Better TOML, and the mypy type checker extension). This doesn't install anything by itself; it's what makes VS Code pop up "this workspace recommends installing..." for anyone who opens the folder without those extensions.
- **`.vscode/launch.json`** — three debug configurations: run/debug whatever test file is currently open, run/debug the (future) sweep runner against a small smoke config, and run/debug whatever script is open with prompted command-line arguments.
- **`.vscode/tasks.json`** — four one-click tasks: run the full test suite, run the linter, run `make figures`, and run a smoke-scale sweep.

## Why commit editor config at all

The honest reason: without it, every command in this 42-day plan implicitly assumes "the right virtual environment is active and the right tools are configured," and that assumption silently breaks the moment this project is opened on a different machine, or after a long gap, or by anyone else entirely. A `.vscode/` folder turns "remember to activate the venv and run the linter before you commit" into "open the folder, VS Code already knows." For a project whose whole point is *reproducibility* (see the contribution claim), that consistency matters structurally, not just as a convenience.

## Environment note (real, not glossed over)

The plan calls for Python 3.11+. This machine only has Python 3.10.12 installed system-wide (confirmed: no `python3.11`, `python3.12`, or `python3.13` binary present, and I didn't install a new Python version without checking first, since that's a bigger system change than anything else today). Everything in this project runs fine on 3.10 with one adjustment: 3.11 added `tomllib` to the standard library, so on 3.10 the project depends on the `tomli` package instead for reading TOML config files. This is noted here so it doesn't look like a silent scope change later — `pyproject.toml`'s `requires-python` will say `>=3.10`, not `>=3.11`.

Venv creation also hit the same `/mnt/c` quirk documented for the original `quadrature-interferometer-sim` project (`ensurepip` not available, so `python3 -m venv` builds the directory structure but not `pip`) — same fix applied: venv lives on the native WSL filesystem at `/home/nishadrobotics/venvs/hoqi-bench` (not inside the repo folder itself), pip bootstrapped via `get-pip.py`, source code stays on the Windows drive so it's still visible to VS Code and OneDrive/GitHub Desktop workflows.

## What was actually verified (not just written)

Per the instruction to verify rather than trust config:

1. **pytest discovery**: wrote a throwaway `tests/test_sanity.py`, ran `pytest --collect-only` (found it) and `pytest -v` (passed), then deleted it — its only job was proving discovery works, and it's captured here instead of left in the repo as clutter.
2. **Format-on-save**: ran `ruff format` directly on a deliberately badly-formatted sample file and confirmed it reformatted correctly (consistent spacing, blank line before the function). This is the exact mechanism VS Code's format-on-save calls under the hood, so this is a real proof, not a guess — though I can't literally press Ctrl+S in the VS Code GUI from here.
3. **Jupyter against the venv**: registered the venv as a named Jupyter kernel (`hoqi-bench`), then executed a real notebook cell against it headlessly (`import numpy as np; np.array([1,2,3]).sum()`) and got back the correct output (`6`) through the actual kernel — confirms the kernel is wired to the right Python and the right packages, not just installed.
4. **What I could NOT verify from here, and want to be upfront about**: actually hitting a breakpoint in the VS Code debugger UI requires driving the VS Code application itself, which isn't something I have access to from this terminal-only environment. What I *did* verify: `debugpy` (the engine VS Code's debugger uses) is installed and importable in the venv, and all four `.vscode/*.json` files parse as valid JSON. The first time you actually set a breakpoint and hit F5, that's a real, still-needed check on your end — flagging this now rather than claiming something I didn't actually test.

## Reproducing this environment elsewhere

```bash
python3 -m venv /home/nishadrobotics/venvs/hoqi-bench   # or wherever suits a different machine
/home/nishadrobotics/venvs/hoqi-bench/bin/pip install numpy scipy sympy matplotlib pytest pytest-cov ruff mypy tomli pandas pyarrow ipykernel nbclient nbformat debugpy
```

(Day 7 replaces this ad-hoc list with a proper `pyproject.toml` and locked dependencies — this is deliberately informal for Day 0, just enough to get the workspace live.)
