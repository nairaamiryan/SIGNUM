# Pre-commit hooks

Every `git commit` runs automated checks on the files you staged, so broken or
badly formatted code does not reach the repository. The checks are set up with
[Husky](https://typicode.github.io/husky/) (Git hooks) and
[lint-staged](https://github.com/lint-staged/lint-staged) (run tools on staged files).

## What runs

The checks depend on **which files are staged**. A change in `web/` never runs the
Python checks, and a change in `gesture-service/` never runs the Next.js checks.
Files outside both folders (docs, README) are not checked.

| Staged files                | Checks, in this order                                               |
| --------------------------- | ------------------------------------------------------------------- |
| `web/` (`.ts`, `.tsx`, `.js`, `.mjs`, `.json`, `.css`) | ESLint (`--fix`), Prettier (`--write`), TypeScript (`tsc --noEmit`), Vitest (tests related to the staged files) |
| `gesture-service/*.py`      | Ruff lint (`--fix`), Ruff format, Mypy (whole service), Pytest (all tests) |

- Fixes made by ESLint, Prettier and Ruff are added to the commit automatically.
- If any check fails, the commit is **not created**. Fix the reported problem, stage
  the file again and commit again.
- Mypy ignores missing types of third-party libraries. Torch, NumPy, Datasets and
  Hugging Face Hub are treated as untyped, and `spoter/` (legacy research code) is
  not type checked. See `gesture-service/pyproject.toml`.

## One-time setup

You need Node.js 20.19 or newer, Python 3.11 or newer and Git.

1. Repository root: install Husky and lint-staged. This also registers the Git hook.

   ```powershell
   npm install
   ```

2. Web app: install its dependencies (Prettier and Vitest are dev dependencies).

   ```powershell
   cd web
   npm install
   cd ..
   ```

3. Gesture service: create the virtual environment (once) and install the tools.

   ```powershell
   cd gesture-service
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements-dev.txt
   cd ..
   ```

   On macOS and Linux activate it with `source venv/bin/activate`.

The hook finds the `venv` (or `.venv`) of `gesture-service/` by itself, so it works
even when the environment is not activated in your terminal.

## Running the checks by hand

```powershell
# web/
npm run lint            # ESLint
npm run format:check    # Prettier, check only (npm run format fixes the files)
npm run typecheck       # TypeScript
npm test                # Vitest

# gesture-service/ (with the venv activated)
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -q
```

## Baseline formatting

Prettier and Ruff were introduced after most of the code was written. The first
formatting pass was done once, in its own commit ("chore: baseline formatting"), so
later pull requests only contain the lines their authors really changed.

## Troubleshooting

- **The hook does not run.** Run `npm install` in the repository root, then check
  `git config core.hooksPath`. It must print `.husky/_`.
- **`No module named ruff` (or `mypy`).** Run `pip install -r requirements-dev.txt`
  in `gesture-service/` with the virtual environment active.
- **`Could not run Python`.** The `venv` folder is missing. Follow step 3 of the setup.
- **A check fails on a file you did not change.** Mypy and Pytest check the whole
  service, ESLint and TypeScript the whole web app. Fix the reported problem or
  ask the team.
- **Skip the hook in an emergency.** `git commit --no-verify`. Use it rarely; the
  same problems will be found later by reviewers.
- **CI and deployment.** Set `HUSKY=0` when running `npm install` on a server so
  that no Git hook is installed there.
