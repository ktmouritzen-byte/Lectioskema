# Copilot instructions (Lectio)

## Environment policy (IMPORTANT)
- Do **not** create or manage Python virtual environments in this repo.
  - Never run: `python -m venv ...`, `py -m venv ...`, `virtualenv ...`, `conda create ...`, `pipenv ...`, `poetry env ...`.
  - Never add a new `.venv/` or `venv/` folder.
- Assume the user already has a working Python interpreter selected in VS Code.
  - If you need Python, use the currently selected interpreter.
  - If Python dependencies are missing, **stop and ask** before installing anything.

## Dependency installation
- Do not run `pip install ...` automatically.
- If installs are required, propose commands for the user to run in their existing environment (no venv creation), e.g.:
  - `py -m pip install -e .`
  - `py -m pip install -r requirements.txt`

## Scripts
- Prefer using the existing PowerShell scripts under `scripts/`.
- If setup seems needed, prefer running `scripts/bootstrap.ps1` (it must not create venvs).
