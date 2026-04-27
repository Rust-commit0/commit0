# Rust Test Suite Report — commit0 Harness

**Date**: Apr 27, 2026  
**Location**: `commit0/harness/tests/` and `agent/tests/`  
**Total Files**: 23  
**Total Test Functions**: **1,190**

---

## Summary by File

| # | File | Lines | Tests | Module Under Test | Status |
|---|---|---|---|---|---|
| 1 | `test_agent_utils_rust.py` | 1,408 | 126 | `agent_utils_rust` | ✅ Complete |
| 2 | `test_lint_rust_expanded.py` | 1,072 | 110 | `lint_rust` | ✅ Complete |
| 3 | `test_run_rust_tests.py` | 1,112 | 100 | `run_rust_tests` | ✅ Complete |
| 4 | `test_evaluate_rust.py` | 938 | 92 | `evaluate_rust` | ✅ Complete |
| 5 | `test_constants_rust.py` | 569 | 91 | `constants_rust` | ✅ Complete |
| 6 | `test_docker_build_rust.py` | 2,013 | 90 | `docker_build_rust` | ✅ Complete |
| 7 | `test_spec_rust.py` | 500 | 79 | `spec_rust` | ✅ Complete |
| 8 | `test_rust_test_parser.py` | 585 | 56 | `rust_test_parser` | ✅ Complete |
| 9 | `test_patch_utils_rust.py` | 312 | 55 | `patch_utils_rust` | ✅ Complete |
| 10 | `test_health_check_rust.py` | 300 | 52 | `health_check_rust` | ✅ Complete |
| 11 | `test_build_rust.py` | 443 | 49 | `build_rust` | ✅ Complete |
| 12 | `test_lint_filter_rust.py` | 273 | 45 | `lint_filter` (cross-cutting) | ✅ Complete |
| 13 | `test_setup_rust.py` | 537 | 38 | `setup_rust` | ✅ Complete |
| 14 | `test_dockerfiles_rust.py` | 227 | 36 | `dockerfiles_rust` | ✅ Complete |
| 15 | `test_security_rust.py` | 376 | 34 | `save`, `docker_utils`, `cli` (cross-cutting) | ✅ Complete |
| 16 | `test_rust_modules.py` | 342 | 26 | Multiple (integration) | ✅ Complete |
| 17 | `test_string_brutality_rust.py` | 184 | 24 | String handling (cross-cutting) | ✅ Complete |
| 18 | `test_type_coercion_rust.py` | 230 | 20 | YAML/config coercion (cross-cutting) | ✅ Complete |
| 19 | `test_save_error_recovery_rust.py` | 441 | 19 | `save` (cross-cutting) | ✅ Complete |
| 20 | `test_integration_smoke_rust.py` | 154 | 16 | CLI/agent flow (cross-cutting) | ✅ Complete |
| 21 | `test_config_class_rust.py` | 178 | 12 | `Commit0Config` (cross-cutting) | ✅ Complete |
| 22 | `test_concurrency_rust.py` | 265 | 10 | ThreadPool/multiprocessing (cross-cutting) | ✅ Complete |
| 23 | `test_error_recovery_rust.py` | 169 | 10 | Error recovery (cross-cutting) | ✅ Complete |
| | **TOTAL** | **12,628** | **1,190** | | |

---

## Coverage Breakdown by Module

### Deep Coverage (80+ tests)

- **`agent_utils_rust`** (126 tests) — Agent utility functions for Rust repos. Comprehensive edge-case and validation testing.
- **`lint_rust`** (110 tests) — `_find_cargo_toml`, `_run_cargo_clippy`, `_run_cargo_fmt`, `_collect_rs_files`, `main()`. Clippy JSON parsing, span extraction, timeouts, edge cases.
- **`run_rust_tests`** (100 tests) — `main()` end-to-end: repo matching, git loading, branch handling, patch/eval writing, backend routing, timeouts, verbose, exceptions.
- **`evaluate_rust`** (92 tests) — `_aggregate_rust_results` (nextest, cargo fallback, edge cases, OS errors), `main()` (dataset loading, splits, threading, CSV output, logging, backends).
- **`constants_rust`** (91 tests) — All constants, `RUST_SPLIT` dict, path constants, `RustRepoInstance` model (validation, serialization, equality, edge fields), `TestStatus` enum, gitignore entries.
- **`docker_build_rust`** (90 tests) — `build_base_images_rust` (skip/rebuild/platform/cert), `get_rust_repo_configs_to_build` (stale detection, timestamp errors), `build_rust_repo_images` (parallel execution, error handling, logging, progress bar).

### Moderate Coverage (30–79 tests)

- **`spec_rust`** (79 tests) — `RustSpec` class, `make_rust_spec`, `get_rust_specs_from_dataset`. Dockerfile generation, repo/eval scripts, edge cases for test_cmd resolution, patch paths, script ordering.
- **`rust_test_parser`** (56 tests) — `parse_nextest_json`, `parse_nextest_report`, `RustTestResult`, `_EVENT_STATUS_MAP`. All four status mappings, malformed input, mixed valid/invalid lines, summary counts, dataclass equality.
- **`patch_utils_rust`** (55 tests) — Target detection, filtering, validation, generation. Parametrized edge cases, performance.
- **`health_check_rust`** (52 tests) — `_RUST_TOOLS` structure, `_check_tool` (success/failure/timeout), `main()` (prints, logging, parametrized failures).
- **`build_rust`** (49 tests) — `_load_datasets` (JSON variants, directory, dict-to-list, sorted glob), `main()` (workers, verbose, Docker client, partial failure, logging, exit codes).
- **`lint_filter`** (45 tests) — Cross-cutting lint filter logic.
- **`setup_rust`** (38 tests) — `main()` filtering (split/name/dash-underscore normalization), cloning (URL format, absolute dirs), branch handling (JSON path, slash extraction, lowering, deletion), gitignore (partial overlap, exception logging, all-present).
- **`dockerfiles_rust`** (36 tests) — Base/repo dockerfile generation. Template handling, FROM line, proxy args, ordering.
- **`security`** (34 tests) — Shell injection, credential exposure, YAML bombs across save, docker_utils, cli.

### Light Coverage (< 30 tests)

- **`test_rust_modules.py`** (26 tests) — Integration cross-module sanity checks.
- **`string_brutality`** (24 tests) — Unicode, special characters in repo names, paths, IDs.
- **`type_coercion`** (20 tests) — YAML type coercion, config validation, Pydantic model edges.
- **`save_error_recovery`** (19 tests) — Silent push failures, credential handling in save.py.
- **`integration_smoke`** (16 tests) — CLI invocations and agent flow mocks.
- **`config_class`** (12 tests) — `Commit0Config` dataclass and config file handling.
- **`concurrency`** (10 tests) — ThreadPoolExecutor, multiprocessing.Pool patterns.
- **`error_recovery`** (10 tests) — Bare except block behavior across modules.

---

## Key Testing Patterns Used

- **Heavy mocking** — `unittest.mock.patch` throughout, no real Docker/Git/subprocess calls
- **Parametrized tests** — `@pytest.mark.parametrize` in lint, health_check, patch_utils, constants
- **Class-based grouping** — Most files use `TestCase` classes organized by function under test
- **Edge case focus** — Empty inputs, missing files, permission errors, timeouts, unicode, special characters

---

**Bottom line**: All 23 Rust test files have comprehensive test suites totaling **1,190** test functions across **12,628** lines of test code. Full module coverage achieved. All files follow the `*_rust*` naming convention.
