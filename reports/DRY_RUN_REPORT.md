# Dry Run Report — commit0 Rust Pipeline

**Date**: 2026-04-24
**Analyst**: AI Static Analysis (Mental Execution)
**Target**: `commit0` Rust Pipeline — AI coding agent benchmark framework for Rust repositories
**Version**: v0.1.8
**Scope**: All 28 Rust-specific source files + shared infrastructure

---

## Step 0 — Target Classification

| Attribute | Value |
|---|---|
| Language | Python 3.12+ (host tooling), Rust 1.88.0 (target repos) |
| Framework | Typer CLI, Docker SDK, Modal, E2B, GitPython, aider-chat (forked) |
| Paradigm | Mixed: OOP (ABCs, dataclasses) + Procedural + Event-driven (multiprocessing) |
| Build System | Hatchling (Python), Cargo (Rust targets) |
| Concurrency | multiprocessing.Pool, ThreadPoolExecutor, threading (Docker exec timeout) |
| External Dependencies | Docker daemon, Modal cloud, E2B sandbox, GitHub API, HuggingFace Hub, LLM APIs (OpenAI/Anthropic/Google/Bedrock) |
| Target Repos | 6 Rust crates: taffy, bon, grex, tide, ocrs, gimli |

### Entry Points

| Entry Point | File | Mechanism |
|---|---|---|
| `agent rust run` | `agent/cli_rust.py:22` | Typer CLI → `run_rust_agent()` |
| `run_pipeline_rust.sh` | `run_pipeline_rust.sh` | Bash script — 3-stage pipeline (Draft → Lint Refine → Test Refine) |
| `commit0 build` (Rust) | `commit0/harness/build_rust.py:41` | Python entry — builds Docker images |
| `commit0 test` (Rust) | `commit0/harness/run_rust_tests.py:70` | Python entry — runs tests in Docker/Modal/E2B |
| `commit0 evaluate` (Rust) | `commit0/harness/evaluate_rust.py:147` | Python entry — parallel evaluation across repos |

### File Inventory (28 files)

| Category | Files |
|---|---|
| CLI & Entry | `agent/cli_rust.py`, `run_pipeline_rust.sh` |
| Constants & Models | `commit0/harness/constants_rust.py` |
| Setup | `commit0/harness/setup_rust.py` |
| Spec & Docker | `commit0/harness/spec_rust.py`, `commit0/harness/dockerfiles/__init__rust.py`, `commit0/harness/dockerfiles/Dockerfile.rust` |
| Build | `commit0/harness/docker_build_rust.py`, `commit0/harness/build_rust.py` |
| Test & Eval | `commit0/harness/run_rust_tests.py`, `commit0/harness/evaluate_rust.py`, `commit0/harness/rust_test_parser.py` |
| Lint | `commit0/harness/lint_rust.py` |
| Health Check | `commit0/harness/health_check_rust.py` |
| Patch | `commit0/harness/patch_utils_rust.py` |
| Agent | `agent/agents_rust.py`, `agent/agent_utils_rust.py`, `agent/run_rust_agent.py` |
| Prompt | `agent/prompts/rust_system_prompt.md` |
| Shared (Python pipeline) | `commit0/harness/execution_context.py`, `commit0/harness/docker_utils.py`, `commit0/harness/docker_build.py`, `commit0/harness/spec.py`, `commit0/harness/utils.py`, `agent/agents.py`, `agent/run_agent.py` |

---

## Phase 1 — Structural Mapping

### 1.1 Control Flow Graph

#### Pipeline A: CLI-Based (`agent rust run`)

```
agent/cli_rust.py:run()
  └─ agent/run_rust_agent.py:run_rust_agent()
       ├─ commit0/cli.py:read_commit0_config_file()        # layering violation
       ├─ commit0/harness/utils.py:load_dataset_from_config()
       ├─ Filter repos by RUST_SPLIT
       ├─ multiprocessing.Pool(num_workers)
       │    └─ run_rust_agent_for_repo()   [per repo, forked process]
       │         ├─ DirContext(repo_path)   # os.chdir
       │         ├─ git: create/checkout branch
       │         ├─ agent_utils_rust.py:get_target_edit_files_rust()
       │         │    └─ find files with STUB_MARKER
       │         ├─ agent_utils_rust.py:extract_rust_function_stubs()
       │         │    └─ regex _FN_PATTERN + brace-depth counting
       │         ├─ For each target file:
       │         │    ├─ Build prompt (inline get_rust_message)
       │         │    ├─ agents_rust.py:RustAiderAgents.run()
       │         │    │    ├─ Redirect stdout/stderr to log
       │         │    │    ├─ Create aider Coder with Rust lint_cmds
       │         │    │    └─ Run coder (LLM interaction)
       │         │    └─ git add + commit
       │         └─ Queue.put(repo_name)   # progress tracking
       └─ Collect results, print progress
```

#### Pipeline B: Shell-Based (`run_pipeline_rust.sh`)

```
run_pipeline_rust.sh
  ├─ Preflight checks (Python, venv, repos, API probe)
  ├─ Model preset selection (opus/kimi/glm5/minimax/nova-premier/etc.)
  ├─ Config file generation (.commit0.yaml, .agent.yaml)
  ├─ Stage 1: DRAFT
  │    ├─ agent rust run (via Python CLI)
  │    ├─ Watchdog (inactivity/hard/absolute timeouts)
  │    └─ Direct cargo test evaluation (NO Docker)
  ├─ Stage 2: LINT_REFINE
  │    ├─ agent rust run (same mechanism)
  │    ├─ Watchdog
  │    └─ Direct cargo test evaluation
  ├─ Stage 3: TEST_REFINE
  │    ├─ agent rust run (same mechanism)
  │    ├─ Watchdog
  │    └─ Direct cargo test evaluation
  ├─ Cost extraction from aider logs
  ├─ JSON results compilation
  └─ Cleanup trap (kill watchdog, subprocesses)
```

#### Pipeline C: Docker-Based Test/Evaluate

```
commit0/harness/build_rust.py:main()
  ├─ _load_datasets() → load JSON or glob *_rust_dataset.json
  ├─ get_rust_specs_from_dataset() → RustSpec objects
  ├─ build_base_images_rust() → single base image
  └─ build_rust_repo_images() → ThreadPoolExecutor parallel build
       └─ docker_build.py:build_image()  # shared with Python pipeline
            ├─ Step 1: buildx build → OCI tarball
            └─ Step 2: docker load from tarball

commit0/harness/run_rust_tests.py:main()
  ├─ load_dataset_from_config()
  ├─ Find matching RustRepoInstance
  ├─ Create RustSpec → eval script
  ├─ Dispatch to ExecutionContext (Docker/Modal/E2B)
  ├─ Read cargo_test_exit_code.txt   ← MISMATCH: spec writes test_exit_code.txt
  └─ sys.exit(exit_code)

commit0/harness/evaluate_rust.py:main()
  ├─ _preflight_check_images()
  ├─ ThreadPoolExecutor(max_workers=num_workers)
  │    └─ Per repo: run_rust_tests.main() → catch SystemExit
  ├─ _aggregate_rust_results()
  │    ├─ Parse nextest JSON (preferred)
  │    └─ Fallback: parse cargo test stdout
  └─ Print CSV results
```

### 1.2 Call Graph — Key Chains

| Chain | Path |
|---|---|
| Agent run | `cli_rust.run` → `run_rust_agent` → `Pool.apply_async(run_rust_agent_for_repo)` → `RustAiderAgents.run` → aider Coder |
| Build | `build_rust.main` → `build_base_images_rust` → `build_image` (2-step OCI+load) |
| Test | `run_rust_tests.main` → `RustSpec.make_eval_script_list` → `ExecutionContext.exec_run_with_timeout` |
| Evaluate | `evaluate_rust.main` → `ThreadPoolExecutor` → `run_rust_tests.main` per repo → `_aggregate_rust_results` |
| Pipeline | `run_pipeline_rust.sh` → `agent rust run` (subprocess) → direct `cargo test` eval |

### 1.3 Dependency Map

#### Internal Dependencies
```
agent/cli_rust.py
  └─ imports: run_rust_agent (from run_rust_agent.py)

agent/run_rust_agent.py
  └─ imports: commit0.cli.read_commit0_config_file  ← LAYERING VIOLATION
  └─ imports: commit0.harness.utils (load_dataset, clone_repo, setup_logger)
  └─ imports: commit0.harness.constants_rust (RustRepoInstance, RUST_SPLIT, RUST_STUB_MARKER)
  └─ imports: agent.agent_utils_rust (get_target_edit_files_rust, extract_rust_function_stubs)
  └─ imports: agent.agents_rust (RustAiderAgents)
  └─ imports: agent.run_agent (DirContext)

agent/agents_rust.py
  └─ inherits: agent.agents.AiderAgents  ← copies entire run() method (220 lines)
  └─ imports: agent.agent_utils_rust (get_lint_cmd_rust)

commit0/harness/spec_rust.py
  └─ inherits: commit0.harness.spec.Spec
  └─ imports: commit0.harness.constants_rust

commit0/harness/docker_build_rust.py
  └─ imports: commit0.harness.docker_build (build_image, _safe_builder_args)

commit0/harness/evaluate_rust.py
  └─ imports: commit0.harness.run_rust_tests
  └─ imports: commit0.harness.rust_test_parser

commit0/harness/run_rust_tests.py
  └─ imports: commit0.harness.execution_context (Docker, Modal, E2B)
  └─ imports: commit0.harness.spec_rust (RustSpec)
```

#### External Dependencies (Risk Profile)

| Dependency | Risk | Notes |
|---|---|---|
| Docker daemon | HIGH | Required for build/test/evaluate; no pre-check |
| Rust 1.88.0 | HIGH | Hardcoded in Dockerfile; pipeline assumes host toolchain |
| Modal cloud | MEDIUM | Lazy-imported; sandbox API may change |
| E2B sandbox | MEDIUM | 1-hour auto-expiry; setup.sh must complete first |
| LLM APIs | HIGH | API keys in env; rate limits; token limits; cost |
| GitHub API | MEDIUM | Rate limit retry up to 5 hours |
| HuggingFace Hub | LOW | Dataset loading; offline fallback possible via JSON |
| aider-chat (fork) | HIGH | Heavily monkey-patched; breakage on update |

### 1.4 Structural Issues

| Issue | Severity | Location |
|---|---|---|
| `run_rust_agent.py` imports `read_commit0_config_file` from `commit0.cli` | HIGH | Layering violation: agent → CLI |
| `RustAiderAgents.run()` copies entire 220-line parent method | HIGH | Maintenance bomb — diverges silently |
| Two prompt builders: `get_rust_message` (inline in run_rust_agent) vs `get_message_rust` (agent_utils_rust) | MEDIUM | Dead code + confusion |
| Two evaluation paths: pipeline (direct cargo test) vs Python (Docker-based) | MEDIUM | Different semantics, different counting |
| Two config systems: pipeline writes per-run files vs CLI uses static files | MEDIUM | No shared abstraction |
| `setup_rust.py` never called from pipeline | MEDIUM | Pipeline relies on pre-existing clones |
| Three different test ID handling mechanisms | MEDIUM | Inconsistency across paths |
| No shared abstractions with Python pipeline | HIGH | Massive code duplication across ~28 files |

---

## Phase 2 — Data Flow Analysis

### 2.1 Taint Analysis

#### CRITICAL: Shell Injection via Test IDs

**Source**: Dataset JSON → `test_ids` field
**Sink**: `spec_rust.py:71` — `eval_cmd.format(test_ids=test_ids)`

```python
# spec_rust.py:69-72
f"{test_cmd} {test_ids} 2>&1 | tee /log/test_output.txt\n"
f"echo $? > /log/test_exit_code.txt\n"
```

Test IDs from the dataset are interpolated directly into a bash script without `shlex.quote()`. A malicious test ID like `; rm -rf /` would execute arbitrary commands inside the container.

**Also affects**: `run_rust_tests.py:122` where the eval script is generated.

#### CRITICAL: Unquoted Shell Variables in Pipeline

**Source**: Dataset JSON → `test_cmd` field
**Sink**: `run_pipeline_rust.sh:864`

```bash
eval "$test_cmd $test_filter" 2>&1 | tee "$log_file"
```

The `$test_cmd` from dataset JSON is directly `eval`'d in bash. If the dataset contains a malicious test command, it executes with full user privileges on the host (not in Docker).

#### HIGH: Git Clone URL Injection

**Source**: Dataset JSON → `repo` field
**Sink**: `spec_rust.py:47` — `git clone`

```python
f"git clone -o origin https://github.com/{repo_name}.git /testbed"
```

Repo name is not validated. A repo name containing shell metacharacters could inject arguments into git.

#### HIGH: API Keys & Credentials Flow

| Credential | Source | Flow | Risk |
|---|---|---|---|
| GitHub token | CLI arg / env | `save.py:49` embeds in git remote URL → persisted in `.git/config` | Token on disk |
| OpenAI API key | `OPENAI_API_KEY` env | `agents.py:481` → aider → LLM API | Standard |
| Anthropic key | `ANTHROPIC_API_KEY` env | `agents.py:484` → aider → LLM API | Standard |
| AWS creds | `AWS_*` env vars | Direct Bedrock auth (SigV4/Bearer) | Standard |
| Bearer token | `BEDROCK_BEARER_TOKEN` | `run_pipeline_rust.sh:171-181` → unsets IAM creds irreversibly | Shell session mutation |

#### MEDIUM: Dataset as Trust Boundary

The entire pipeline trusts dataset JSON implicitly:
- `test_cmd` → executed as shell command
- `test_ids` → interpolated into bash scripts
- `repo` → used in git clone URLs
- `base_commit` → used in git checkout/reset
- No schema validation anywhere

### 2.2 Null/None Propagation

| Location | Issue | Severity |
|---|---|---|
| `run_rust_tests.py:193` | `int()` on file content that may not exist → `FileNotFoundError` or `ValueError` | HIGH |
| `agent_utils_rust.py:237` | `get_rust_test_ids()` returns empty list silently → runs ALL tests instead of targeted | HIGH |
| `evaluate_rust.py:286` | Hardcoded `split("/")[2]` on log path → `IndexError` on unexpected path format | HIGH |
| `run_rust_tests.py:81-83` | Substring matching `if repo_name in ds_repo` could false-positive | MEDIUM |
| `spec_rust.py:142-143` | Dict access on potentially wrong instance type → `KeyError` | MEDIUM |
| `constants_rust.py` | `RustRepoInstance` inherits Optional fields from `RepoInstance` — no default for `edition`/`features`/`workspace` | MEDIUM |

### 2.3 Value Range Analysis

| Parameter | Expected | Actual Validation | Risk |
|---|---|---|---|
| `timeout` | Positive integer (seconds) | None | 0 or negative → immediate timeout |
| `num_cpus` | Integer for Docker nano_cpus | None | `nano_cpus=1` means 1 nanosecond of CPU — effectively zero |
| `num_workers` | Positive integer for pool/executor | None | 0 → deadlock; very large → resource exhaustion |
| `max_retries` (GitHub) | 10 (hardcoded) | — | Can block for 5+ hours |
| E2B sandbox timeout | 3600s (hardcoded) | — | May expire during long builds |
| Pipeline watchdog timeouts | Configurable | Validated in bash | Reasonable |

### 2.4 Data Transformation Chain

```
Dataset JSON
  → RustRepoInstance (Pydantic model, minimal validation)
    → RustSpec (generates Dockerfile + eval script)
      → Docker build (OCI tarball → image)
        → Container exec (bash eval script)
          → stdout + exit code file
            → rust_test_parser (nextest JSON or raw text)
              → {passed, failed, error} counts
                → CSV output
```

**Weak links**: No schema validation on dataset. No exit code file validation. Parser has two fallback modes with different counting semantics.

---

## Phase 3 — State & Mutation Analysis

### 3.1 Implicit State Machines

#### Docker Container Lifecycle

```
[Created] → [Started] → [Exec Running] → [Exec Complete] → [Killed] → [Removed]
     ↓ fail      ↓ fail        ↓ timeout         ↓ fail          ↓ fail
  [Orphaned]  [Orphaned]   [Thread Leak]     [Orphaned]    [Zombie Container]
```

**Issue**: Container created in `__init__` (`execution_context.py:111`), not `__enter__`. If `__init__` fails after `create_container()`, no `__exit__` runs → orphaned container.

#### Git Repository State

```
[Clean] → [Branch Created] → [Files Modified] → [Committed] → [Pushed]
                                    ↓ agent crash
                               [Dirty Working Tree]
                                    ↓ next run
                               [Conflicts / Stale State]
```

**Issue**: Pipeline stages share the same working tree. If Stage 1 crashes mid-edit, Stage 2 starts from corrupt state.

#### Agent Session State

```
[Init] → [File Discovery] → [Stub Extraction] → [Per-File Loop] → [Done]
                                                       ↓ LLM fail
                                                  [Partial Edits]
                                                       ↓ retry
                                                  [Stacked Diffs]
```

### 3.2 Shared Mutable State

| State | Scope | Hazard | Severity |
|---|---|---|---|
| `sys.stdout` / `sys.stderr` | Process-global | `agents_rust.py:72-76` redirects globally; unsafe if aider spawns threads | CRITICAL |
| `os.environ` (AWS creds) | Process-global | Helicone removed; AWS creds no longer mutated | RESOLVED |
| `litellm.model_cost` | Module-global | `agents.py:343` mutates global pricing dict | MEDIUM |
| `os.chdir` via `DirContext` | Process-global | Safe in fork (`multiprocessing`), would break under threads | MEDIUM |
| Docker daemon | System-global | Multiple threads issue build/exec/kill commands simultaneously | MEDIUM |
| Docker `DockerClient` | Shared across ThreadPoolExecutor | Not guaranteed thread-safe by Docker SDK | HIGH |
| Git working tree | Filesystem | Pipeline stages share repo — no isolation between stages | MEDIUM |
| Log files | Filesystem | Multiple processes write to same log directory; names include repo but not PID | LOW |
| `.commit0.yaml` / `.agent.yaml` | Filesystem | Pipeline overwrites between stages; concurrent reads possible | MEDIUM |

### 3.3 Resource Lifecycle Issues

| Resource | Creation | Cleanup | Gap |
|---|---|---|---|
| Docker container | `__init__` | `__exit__` (kill+remove) | Orphan if `__init__` fails after create |
| Docker builder | `buildx create` | Never explicitly removed | Accumulates across runs |
| OCI tarball | `build_image()` | Never cleaned | ~500MB-2GB each, persists in `/tmp` |
| Exec thread | `exec_run_with_timeout` | Never `join()`ed | Thread leak on every timeout |
| Modal sandbox | `Sandbox.create()` | `sandbox.terminate()` | Leak if `sandbox.wait()` raises |
| E2B sandbox | `Sandbox()` | Auto-expires (1hr) | May expire during long compilation |
| Log file handles | `setup_logger()` | `close_logger()` | Leaked on exception paths in `run_rust_tests.py` |
| Git index.lock | Git operations | Auto-removed on completion | Orphaned on kill -9 or crash |

---

## Phase 4 — Execution Path Enumeration

### 4.1 Happy Path

**CLI Agent Run (6 repos)**:
1. `agent rust run` → load config, load dataset
2. Filter to Rust repos via `RUST_SPLIT`
3. Spawn `multiprocessing.Pool(num_workers)`
4. Per repo: chdir → create branch → find stubs → extract functions → iterate files
5. Per file: build prompt → `RustAiderAgents.run()` → LLM edits → git commit
6. Collect progress via Queue → print completion

**Pipeline Run (3 stages)**:
1. Preflight: check Python, venv, repos, API connectivity
2. Per stage: write configs → launch `agent rust run` → watchdog monitors → kill on timeout
3. Evaluate: direct `cargo test` per repo → parse output → count pass/fail
4. Aggregate: extract costs from aider logs → produce JSON results

### 4.2 Error Paths

| Trigger | What Happens | Issue |
|---|---|---|
| Docker daemon not running | `DockerException` from `docker.from_env()` | No friendly error; raw traceback |
| Docker image build failure | Exception from `build_image()` | `build_rust_repo_images` returns (success, failed) tuple — caller sys.exit(1) |
| Container exec timeout | Thread sends SIGTERM, waits, then SIGKILL | **Thread never joined** → leak. Timeout thread left running. |
| Exit code file missing | `int(open(...).read())` → `FileNotFoundError` | **Crashes test runner** — unhandled |
| Exit code file mismatch | spec writes `test_exit_code.txt`, runner reads `cargo_test_exit_code.txt` | **ALWAYS crashes in Docker path** — file never exists |
| LLM API failure | aider catches internally, may retry or abort | Agent continues to next file; partial progress committed |
| LLM rate limit | aider retries with backoff | Watchdog may kill if inactivity timeout exceeded |
| Git branch exists | `repo.git.checkout("-b", branch)` fails | Unhandled `GitCommandError` |
| GitHub rate limit | `create_repo_on_github` retries up to 10 times (5hr max) | Blocks entire pipeline |
| HuggingFace unavailable | `load_dataset()` raises | Unhandled in most callers |
| Empty test list | `get_rust_test_ids()` returns `[]` | Runs ALL tests instead of targeted ones |
| `sys.exit()` in ThreadPoolExecutor | `evaluate_rust.py:250` catches `SystemExit` | Fragile; only works because Python converts `sys.exit` to `SystemExit` exception |
| Worker exception in Pool | `result.get()` raises, loop crashes | Remaining workers abandoned (`run_rust_agent.py:542`) |
| Ctrl+C during Pool | Signal handling complex | Pool.terminate() in finally, but ThreadPoolExecutor may hang |
| Cargo compilation failure | Non-zero exit code | Reported as "all tests failed" — indistinguishable from test failure |

### 4.3 Edge Cases

| Scenario | Behavior | Severity |
|---|---|---|
| Repo with no stubs | Empty target file list → agent does nothing → commits nothing | LOW |
| Very large patch (>1MB) | Applied via `git apply` inside container — may timeout | MEDIUM |
| Circular module dependencies | Not applicable (Rust prevents at compile time) | — |
| Unicode in file paths | Python 3 handles; brace-depth counter works with `\w` | LOW |
| Concurrent Docker builds of same image | No locking; race condition on tag | MEDIUM |
| Test ID with spaces/special chars | Shell injection in eval script | CRITICAL |
| Nextest not installed in container | Falls back to `cargo test` — different output format | MEDIUM |
| Brace in string literal | Fools `extract_rust_function_stubs` depth counter | MEDIUM |

### 4.4 Concurrency Paths

#### multiprocessing.Pool (`run_rust_agent.py`)
- **Isolation**: Fork-based → each worker gets copy of parent memory. Safe for `os.chdir`.
- **Communication**: `Manager().Queue()` for progress. `result.get()` for completion.
- **Failure mode**: One worker exception → `result.get()` raises → loop exits → remaining workers orphaned.
- **Signal**: `pool.terminate()` in finally block. Ctrl+C sends SIGINT to all workers.

#### ThreadPoolExecutor (`evaluate_rust.py`, `docker_build_rust.py`)
- **Shared state**: Docker client, file system, log files.
- **No per-future timeout**: Hanging eval blocks the entire executor.
- **`sys.exit()` inside thread**: Caught as `SystemExit` exception — works but fragile.
- **Signal**: Ctrl+C may not interrupt `executor.shutdown(wait=True)`.

#### Threading (`docker_utils.py:exec_run_with_timeout`)
- **Design**: Daemon thread runs Docker exec, main thread waits with timeout.
- **Timeout path**: Main thread sends SIGTERM to container exec, waits 10s, then SIGKILL.
- **Leak**: Thread is never `join()`ed after timeout. Daemon flag means it dies with process, but may accumulate.

---

## Phase 5 — Invariant & Correctness Verification

### 5.1 Precondition Violations

| Function | Assumed Precondition | Violation Scenario | Severity |
|---|---|---|---|
| `build_rust.py:main()` | Docker daemon running | No check; raw `DockerException` | CRITICAL |
| `run_rust_tests.py:main()` | Docker image exists | `_preflight_check_images` only in evaluate path | HIGH |
| `run_rust_agent_for_repo()` | Repo already cloned, branch doesn't exist | No clone check; branch creation fails if exists | HIGH |
| `exec_run_with_timeout()` | Container is running | No state check before exec | MEDIUM |
| `_aggregate_rust_results()` | Log files exist and are valid | `open()` without try/except in some paths | MEDIUM |
| Pipeline `cargo test` | Rust toolchain installed on host | No preflight check for cargo/rustc | CRITICAL |
| `RustSpec.make_eval_script_list()` | `test_ids` is safe for shell | No quoting | CRITICAL |

### 5.2 Postcondition Violations

| Function | Expected Postcondition | Actual | Severity |
|---|---|---|---|
| `build_rust_repo_images()` | Returns (successful, failed) lists | Correct — but caller doesn't retry failed | MEDIUM |
| `run_rust_tests.py:main()` | Exit code reflects test result | Exit code file name mismatch → always crashes | CRITICAL |
| `evaluate_rust.py:main()` | All repos evaluated | Partial failures silently continue; no summary of skipped repos | HIGH |
| `extract_rust_function_stubs()` | Accurate function signatures | Regex fails on nested generics `<Item<'a>>`, closure params `Fn(T)` | MEDIUM |
| `get_rust_test_ids()` | Returns targeted test IDs | Returns `[]` on failure → runs ALL tests | HIGH |

### 5.3 Type Safety Issues

| Location | Issue | Severity |
|---|---|---|
| `nano_cpus` parameter | Receives raw int (1) but Docker expects nanoseconds (1e9) | CRITICAL |
| `int()` on exit code file | No `try/except` for `ValueError` or `FileNotFoundError` | HIGH |
| `float()` on nextest `exec_time` | No `try/except` for `ValueError` | MEDIUM |
| `split("/")[2]` on log paths | Hardcoded index without bounds check | HIGH |
| Dict access on `RepoInstance` vs `RustRepoInstance` | `KeyError` if wrong type passed to spec expecting `edition`/`features` | MEDIUM |
| `RustSpec` inherits `_get_python_version()` | Returns Python version for Rust spec — never called but violates LSP | LOW |

### 5.4 Contract Violations

| Contract | Violation | Severity |
|---|---|---|
| `ExecutionContext.__enter__/__exit__` | Container created in `__init__`, not `__enter__` → cleanup skipped on init failure | HIGH |
| `Spec` ABC | `RustSpec` doesn't override `_get_python_version()` from parent | LOW |
| Test counting | Pipeline counts `rp+rf` as total; evaluate_rust counts `rp+rf+ri` | HIGH — inconsistent metrics |
| `AiderAgents.run()` | `RustAiderAgents.run()` copies entire parent body instead of calling super | HIGH — diverges silently |

---

## Phase 6 — Performance & Resource Projection

### 6.1 Computational Complexity

| Operation | Complexity | Notes |
|---|---|---|
| `extract_rust_function_stubs()` | O(n) per file (line-by-line brace counting) | Efficient |
| `topological_sort_based_on_dependencies()` | O(V+E) with cycle breaking | Efficient |
| `parse_nextest_json()` | O(n) per line | Efficient |
| Cargo compilation | O(crate_graph) — depends on dependency count | **Dominant cost** — no caching in Docker |
| `get_rust_test_ids()` | Spawns `cargo test --list` subprocess | 30-120s per repo (compilation) |
| LLM summarization | 3-tier: deterministic parse → LLM → truncation | LLM path costs tokens |

### 6.2 Memory Hotspots

| Hotspot | Estimated Size | Risk |
|---|---|---|
| Docker exec stdout accumulation | Unbounded (could be 100MB+ for verbose test output) | HIGH — `docker_utils.py:339-340` |
| HuggingFace dataset in memory | ~10-50MB for 6 repos | LOW |
| Tar archive for container copy | Size of entire repo | MEDIUM — large repos with `target/` |
| aider context window | Up to model limit (100K-200K tokens) | MEDIUM — memory for token buffer |
| Multiprocessing (fork) | Each worker duplicates parent memory | MEDIUM — 6 workers × parent size |
| No container memory limits | Docker default (unlimited) | HIGH — Rust compilation can use 4-8GB |

### 6.3 I/O Bottlenecks

| Bottleneck | Impact | Mitigation Present? |
|---|---|---|
| Cargo compilation (no cache) | 5-30 min per repo per test run | **NO** — rebuilds from scratch every time |
| Docker image build | 10-30 min per repo | Stale image detection skips up-to-date |
| Git clone | 1-5 min per repo | One-time setup |
| LLM API latency | 5-60s per request | Inherent; no batching |
| Sequential evaluation (pipeline) | 30-90 min per eval pass × 6 repos | **NO parallelism in pipeline path** |
| Container file copy (tar) | Seconds per operation | Adequate for current scale |

### 6.4 Resource Exhaustion Projections (6 repos, full pipeline)

| Resource | Estimated Usage | Limit Risk |
|---|---|---|
| **Disk (Docker images)** | ~5-8 GB (base + 6 repo images) | LOW |
| **Disk (OCI tarballs)** | ~3-12 GB (never cleaned) | MEDIUM — accumulates |
| **Disk (Cargo target dirs)** | ~2-5 GB per repo | HIGH in pipeline path (host filesystem) |
| **Disk (total peak)** | ~35-50 GB | MEDIUM |
| **RAM (Docker containers)** | 4-8 GB per container (Rust compilation) | HIGH — no memory limits set |
| **RAM (agent processes)** | ~2-6 GB for 6 workers + host | MEDIUM |
| **RAM (total peak)** | 8-16 GB | MEDIUM — depends on parallel workers |
| **CPU** | `nano_cpus=1` → effectively zero CPU allocation | CRITICAL — bug |
| **File descriptors** | ~200-400 peak (logs, Docker, git) | LOW at default 1024 limit |
| **Wall time (pipeline)** | 24-72 hours (3 stages × 6 repos) | Expected |
| **Wall time (evaluation)** | 30-90 min per pass (sequential) | HIGH — no parallelism |
| **LLM cost** | $54-288 (Claude Opus); less for cheaper models | Configurable |
| **Network** | ~5-15 GB (Docker build + LLM API) | LOW |

### 6.5 Key Performance Bottleneck

**No Cargo compilation caching in Docker images.** The Dockerfile does `cargo fetch` during build but doesn't pre-compile. Every `cargo test` invocation inside a container compiles the entire dependency tree from scratch. For repos like `taffy` with many dependencies, this adds 5-30 minutes per test run.

**Fix**: Add `cargo build --tests` or `cargo nextest list` to the Docker image build step to pre-compile dependencies.

---

## Findings Summary Table

| ID | Severity | Phase | Finding | Location |
|---|---|---|---|---|
| R-01 | CRITICAL | P2 | Shell injection: unquoted `{test_ids}` in eval script | `spec_rust.py:71`, `run_rust_tests.py:122` |
| R-02 | CRITICAL | P2 | Shell injection: unquoted `$test_cmd` from dataset JSON | `run_pipeline_rust.sh:864` |
| R-03 | CRITICAL | P5 | Exit code filename mismatch: spec writes `test_exit_code.txt`, runner reads `cargo_test_exit_code.txt` — Docker tests ALWAYS crash | `spec_rust.py:72` vs `run_rust_tests.py:155,191` |
| R-04 | CRITICAL | P5 | `nano_cpus=1` means 1 nanosecond of CPU — Docker containers get near-zero compute | `execution_context.py:115`, `docker_utils.py:293` |
| R-05 | CRITICAL | P6 | No Cargo pre-compilation in Docker images — every test run recompiles from scratch | `Dockerfile.rust`, `spec_rust.py:55` |
| R-06 | CRITICAL | P3 | `sys.stdout/stderr` redirect is process-global — unsafe under threading | `agents_rust.py:72-76` |
| R-07 | CRITICAL | P4 | Pipeline evaluates without Docker isolation — assumes host Rust toolchain | `run_pipeline_rust.sh:860-865` |
| R-08 | HIGH | P3 | Container created in `__init__` not `__enter__` — orphan on init failure | `execution_context.py:111-119` |
| R-09 | HIGH | P3 | Thread never joined after exec timeout — leak per timeout event | `docker_utils.py:353-357` |
| R-10 | HIGH | P4 | `sys.exit()` inside ThreadPoolExecutor — fragile pattern | `run_rust_tests.py:194`, `evaluate_rust.py:250` |
| R-11 | HIGH | P5 | `get_rust_test_ids()` returns `[]` on failure → runs ALL tests | `agent_utils_rust.py:237` |
| R-12 | HIGH | P5 | `int()` on missing/corrupt exit code file — unhandled exception | `run_rust_tests.py:193` |
| R-13 | HIGH | P2 | GitHub token persisted in `.git/config` via remote URL | `save.py:49-51` |
| R-14 | HIGH | P2 | AWS credentials popped globally from `os.environ` | `agents.py:466-469` |
| R-15 | HIGH | P3 | Shared `DockerClient` across ThreadPoolExecutor — not thread-safe | `evaluate_rust.py`, `docker_build_rust.py` |
| R-16 | HIGH | P1 | `RustAiderAgents.run()` is 220-line copy of parent — maintenance bomb | `agents_rust.py` |
| R-17 | HIGH | P5 | Test counting inconsistency: pipeline `rp+rf` vs evaluate `rp+rf+ri` | `run_pipeline_rust.sh:895` vs `evaluate_rust.py:118` |
| R-18 | HIGH | P4 | `result.get()` loop crashes on first error — abandons remaining workers | `run_rust_agent.py:542-543` |
| R-19 | HIGH | P3 | No container memory limits — Rust compilation can OOM host | `docker_utils.py:291-301` |
| R-20 | HIGH | P5 | No Docker pre-check — raw `DockerException` traceback | `build_rust.py:58` |
| R-21 | HIGH | P5 | Hardcoded `split("/")[2]` on log path — `IndexError` on unexpected format | `evaluate_rust.py:286` |
| R-22 | HIGH | P6 | Pipeline evaluation is sequential — 30-90 min per pass, no parallelism | `run_pipeline_rust.sh` |
| R-23 | MEDIUM | P2 | Brace-depth counter fooled by string literals/comments | `agent_utils_rust.py:95-103` |
| R-24 | MEDIUM | P2 | `_FN_PATTERN` regex fails on nested generics and closure params | `agent_utils_rust.py:21-24` |
| R-25 | MEDIUM | P2 | Repo name in git clone URL not validated — injection risk | `spec_rust.py:47` |
| R-26 | MEDIUM | P2 | Bearer token persists in process environment for entire pipeline | `run_pipeline_rust.sh:171-181` |
| R-27 | MEDIUM | P2 | `float()` cast on nextest `exec_time` — uncaught `ValueError` | `rust_test_parser.py` |
| R-28 | MEDIUM | P3 | Pipeline stages share git working tree — corruption across stages | `run_pipeline_rust.sh` |
| R-29 | MEDIUM | P3 | Logger handles leaked on exception paths | `run_rust_tests.py:195-210` |
| R-30 | MEDIUM | P4 | Lint silently reports 0 issues when cargo missing on host | `lint_rust.py` |
| R-31 | MEDIUM | P5 | No dataset validation — Python dataset could be passed to Rust pipeline | Various |
| R-32 | MEDIUM | P5 | Substring repo matching could false-positive | `run_rust_tests.py:81-83` |
| R-33 | MEDIUM | P4 | Partial eval failures indistinguishable from 0-passing-tests | `evaluate_rust.py` |
| R-34 | MEDIUM | P3 | Irreversible `unset` of AWS creds in shell session | `run_pipeline_rust.sh:171-181` |
| R-35 | MEDIUM | P1 | Two config systems — no shared abstraction | Pipeline vs CLI |
| R-36 | MEDIUM | P1 | `setup_rust.py` never called from pipeline | `run_pipeline_rust.sh` |
| R-37 | MEDIUM | P3 | `os.chdir` via DirContext — process-wide, safe with fork only | `run_agent.py` |
| R-38 | MEDIUM | P6 | Docker exec stdout unbounded accumulation | `docker_utils.py:339-340` |
| R-39 | LOW | P1 | Dead code: `get_message_rust()`, `get_lint_cmd_rust()`, `get_rust_file_dependencies()`, `summarize_rust_test_output()`, `get_changed_files_rust()` in agent_utils_rust.py | `agent_utils_rust.py` |
| R-40 | LOW | P1 | `_RUST_PROMPT_PATH` defined in both `agents_rust.py` and `run_rust_agent.py` | Duplication |
| R-41 | LOW | P5 | `RustSpec` inherits `_get_python_version()` from parent Spec | `spec_rust.py` |
| R-42 | LOW | P1 | `CARGO_NEXTEST_VERSION` and `RUST_VERSION` constants never used | `constants_rust.py` |

---

## Recommendations

### Immediate (Block Deployment)

1. **Fix R-03**: Align exit code filename — change `spec_rust.py:72` to write `cargo_test_exit_code.txt` or change `run_rust_tests.py:155,191` to read `test_exit_code.txt`. This is a showstopper: the Docker test path is completely broken.

2. **Fix R-01/R-02**: Quote all shell-interpolated values with `shlex.quote()` in `spec_rust.py` and validate `test_cmd` in pipeline script.

3. **Fix R-04**: Change `nano_cpus` to `nano_cpus=num_cpus * 10**9` to correctly allocate CPU resources.

### Short-Term (Next Sprint)

4. **Fix R-05**: Add `RUN cargo build --tests 2>/dev/null || true` to Docker image build step for compilation caching.

5. **Fix R-08**: Move container creation from `__init__` to `__enter__` in `ExecutionContext.Docker`.

6. **Fix R-09**: Join the exec thread after timeout in `exec_run_with_timeout`.

7. **Fix R-11**: Make `get_rust_test_ids()` raise on failure instead of returning empty list.

8. **Fix R-16**: Refactor `RustAiderAgents.run()` to call `super().run()` with Rust-specific overrides instead of copying the entire method.

9. **Fix R-18**: Wrap `result.get()` in try/except per worker to avoid abandoning remaining workers.

10. **Fix R-19**: Set container memory limits (e.g., `mem_limit="8g"`) for Rust compilation.

### Medium-Term (Technical Debt)

11. **Fix R-22**: Parallelize pipeline evaluation across repos.

12. **Fix R-35/R-36**: Unify config systems and ensure `setup_rust.py` is called from pipeline.

13. **Fix R-17**: Standardize test counting semantics across all paths.

14. **Fix R-15**: Create per-thread `DockerClient` instances or add locking.

15. **Address R-39-42**: Remove dead code and unused constants.

### Architectural

16. **Extract shared abstractions**: Both Python and Rust pipelines duplicate spec/build/test/evaluate patterns. Create a language-agnostic base with language-specific plugins.

17. **Unified evaluation backend**: Currently pipeline uses host `cargo test` while CLI uses Docker. Standardize on Docker-based evaluation for reproducibility.

18. **Dataset validation**: Add JSON schema validation for dataset files to prevent type confusion and injection attacks.

---

## Appendix: Test Execution

This report was generated through static analysis (mental execution) only. No code was modified, no tests were run, and no external services were contacted. All findings are based on reading the source code and reasoning about its behavior.
