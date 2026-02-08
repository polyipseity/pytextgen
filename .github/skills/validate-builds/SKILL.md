# validate-builds

Purpose
-------
Provide a concise, auditable checklist and commands for agents to validate package builds produced by `uv build` and to inspect the generated artifacts (`dist/`). This skill documents both quick manual checks and steps suitable for automation in CI or agent workflows.

Inputs
------
- A checkout of the repository with working `pyproject.toml` and `uv.lock` (if present).
- A Python virtual environment for install/validation steps.

Outputs
-------
- Verified build artifacts in `dist/` (source distribution and wheel).
- A short validation report (pass/fail) including any mismatches or missing files.

Preconditions
-------------
- `uv` (and the pinned `uv_build` backend) is installed and available on PATH.
- Tests and linters have been run and passed locally or in CI.
- The repository declares `uv_build` in `[build-system].requires` for pure-Python packages.

Validation Steps (manual and automated)
---------------------------------------
1. Build the project reproducibly

   - Run: `uv build --locked`
   - Expected: `dist/` contains exactly one sdist (`*.tar.gz`) and one wheel (`*.whl`) matching the project name and version.

2. Inspect artifact filenames and counts

   - Verify wheel filename format: `{name}-{version}-py3-none-any.whl` for pure-Python packages.
   - Verify sdist filename format: `{name}-{version}.tar.gz`.

3. Inspect wheel contents

   - List wheel contents: `python -m zipfile -l dist/*.whl` or `unzip -l dist/*.whl`.
   - Check that the top-level module is present (e.g., `pytextgen/` files) and that small data files are in the module root or `.data` directory as expected.
   - Confirm `.dist-info` metadata exists and contains `METADATA`, `RECORD`, and `entry_points.txt` (if applicable).

4. Inspect sdist contents

   - Extract or list the sdist and confirm `pyproject.toml` and the module source are included.

5. Quick smoke install

   - Create a fresh venv and install the wheel without dependencies: `python -m venv .venv.test && .\.venv.test\Scripts\Activate.ps1` (Windows) or `python -m venv .venv.test && source .venv.test/bin/activate` (POSIX).
   - Install: `python -m pip install --no-deps dist/*.whl`.
   - Verify import and version: `python -c "import pytextgen; print(pytextgen.VERSION)"` (should match `pyproject.toml` version).

6. Validate metadata and license

   - Confirm `project.license` files are copied into `.dist-info` (look for LICENSE files).
   - Confirm `project.readme` is included in package metadata (pip/packaging UI uses it).

7. Optional deeper checks

   - Run a test install from sdist: `python -m pip install --no-deps dist/*.tar.gz` and run the smoke import above.
   - Use `pip show -f pytextgen` to list installed files and confirm layout.

8. Capture build logs and backend version

   - For debugging, enable verbose logs: `RUST_LOG=uv=debug uv build --locked` (or set RUST_LOG=uv=verbose) to confirm which `uv_build` was used.

Automated validation checklist (CI-friendly)
-------------------------------------------
- Run `uv build --locked`.
- Assert that `dist/*.whl` and `dist/*.tar.gz` exist and their names encode the package name and version.
- Run `python -m pip install --no-deps dist/*.whl` in a fresh venv and assert `python -c "import pytextgen; print(pytextgen.VERSION)"` exits 0 and prints the expected version.
- Check `unzip -l dist/*.whl` output contains the module root and `.dist-info/METADATA` with expected license and version strings.

What to report when validation fails
-----------------------------------
- Missing artifact(s) (wheel or sdist).
- Filenames don't match expected `{name}-{version}` pattern.
- Missing top-level module files inside the wheel.
- Installed package import failure or version mismatch.
- Missing license or README in package metadata.

Notes & Tips
-----------
- Always use `--locked` to ensure builds are reproducible with the lockfile.
- For non-pure-Python projects (extension modules), the `uv_build` backend is not suitable; follow the alternative backend guidance in project documentation.
- If using agents, include a small script to run the automated checklist and emit structured JSON or simple pass/fail output for telemetry.

Examples
--------
- Local quick check:

```powershell
uv build --locked
python -m venv .venv.test
.\.venv.test\Scripts\Activate.ps1
python -m pip install --no-deps dist/*.whl
python -c "import pytextgen; print(pytextgen.VERSION)"
```

- Minimal CI job step (psuedocode):

```yaml
- run: uv build --locked
- run: python -m pip install --no-deps dist/*.whl
- run: python -c "import pytextgen; assert pytextgen.VERSION == '$(cat pyproject.toml | grep version | ... )'"
```

---

If you want, I can also add a small validation script (`scripts/validate_build.py`) that implements the automated checklist and returns an exit code and JSON report for agents to consume.
