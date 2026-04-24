# Trajectory Pipeline Flow (Phase 3)

## 1. Per-Repo Initialization

### 1.1 ThinkingCapture Created
- Single `ThinkingCapture()` instance per repo
- Accumulates **all turns** across all stages and modules
- Every turn tagged with: `stage`, `module`, `turn_number`

### 1.2 Target File Discovery

| Language | Function | Logic |
|----------|----------|-------|
| Python | `get_target_edit_files()` | Finds `.py` files with `pass` stubs, topologically sorted by import dependencies |
| Rust | `get_target_edit_files_rust()` | Finds `.rs` files containing `todo!("STUB")` |

### 1.3 Lint File Discovery
- `get_changed_files_from_commits()` → files changed from `base_commit`
- Filters by `.py` or `.rs` based on language

### 1.4 Test File Discovery

| Language | Source |
|----------|--------|
| Python | `get_pytest_ids()` → list of test files |
| Rust | Dataset-provided `test_cmd` as single entry |

---

## 2. Stage 1: Draft

> **Config**: `run_tests=false`, `use_lint_info=false`, `use_unit_tests_info=true`, `add_import_module_to_context=true`

**Iterates**: each target edit file (in dependency order)

### Per-Module Execution

#### A. Prompt Construction (`get_message`)
- User prompt template
- Repo info (description, purpose)
- Unit test names/signatures (**not** results — tests are not run)
- Spec summary (if enabled — LLM-summarized from PDF)
- Import context of dependent modules (Python only)

#### B. Aider Coder Created
- Model configured: `stream=True`, `auto_lint=False`, `auto_test=False`, `max_reflections=max_iteration`
- 6 monkey-patches installed for thinking capture
- Language-specific system prompt appended

#### C. Conversation Loop

1. **User turn captured** → `Turn(role="user", content=prompt, stage="draft", module=file_name)`
2. **LLM called** → streaming response, `reasoning_content` intercepted from SSE chunks
3. **Assistant turn captured** → `Turn(role="assistant", content=response, thinking=reasoning_text, stage="draft", module=file_name)` + token/cost snapshot
4. **SEARCH/REPLACE applied** → edits written to file
   - **Success**: move to next module
   - **Failure**: `edit_error` captured, aider reflects (loops back, up to `max_reflections`)

#### D. Per-Module Output
- `output.json` written (OpenHands event format with metrics)
- `.done` sentinel written (crash recovery)

### After All Draft Modules
- `trajectory.md` written
- `output.jsonl` written
- Cost extracted from `aider.log`

### ✅ Evaluation (Stage 1)
- `commit0 evaluate` → Docker container → run full test suite
- Parse results → aggregate pass/fail/runtime
- Save to `results_stage1.json`

---

## 3. Stage 2: Lint Refine

> **Config**: `run_tests=false`, `use_lint_info=true`, `run_entire_dir_lint=true`

**Iterates**: each lint file (files changed from base)

### Per-Module Execution

#### A. Aider Coder Created
- `auto_lint=True`, `lint_first=True`
- `lint_cmds={"python": cmd}` or `{"rust": cmd}` based on language
- 6 monkey-patches installed

#### B. Conversation Loop

1. **Lint runs first** → output captured as `Turn(role="tool_lint", stage="lint", module=file_name)`
2. **User turn** → lint output + fix instructions sent to LLM
3. **Assistant turn** → LLM proposes fixes, thinking captured
4. **SEARCH/REPLACE applied** → lint re-runs → iterate up to `max_reflections`

> **Note**: When aider spawns an internal `lint_coder` clone, Patch 5 copies ThinkingCapture + all patches to the clone.

#### C. Per-Module Output
- `output.json` + `.done` sentinel

### After All Lint Modules
- `trajectory.md` updated
- Cost extracted (incremental + cumulative)

### ✅ Evaluation (Stage 2)
- Full test suite run again
- Save to `results_stage2.json`

---

## 4. Stage 3: Test Refine

> **Config**: `run_tests=true`, optionally `use_lint_info=true`

**Iterates**: each test file

### Per-Module Execution

#### A. Aider Coder Created
- `auto_test=True`, `test_first=True`
- 6 monkey-patches installed

#### B. Conversation Loop

1. **Tests run first** (before any edits) → raw output captured
2. **Test output summarized** (if output exceeds `max_test_output_length`):
   - **Tier 1**: Deterministic parse — `_parse_pytest_output()` (Python) or `_parse_cargo_test_output()` (Rust)
   - **Tier 2**: LLM summarization
   - **Tier 3**: Smart truncation (fallback)
3. **Tool turn captured** → `Turn(role="tool_test", content=summarized_output, stage="test", module=test_file_name)`
4. **User turn** → test failures + fix instructions sent to LLM
5. **Assistant turn** → LLM proposes fixes, thinking captured
6. **SEARCH/REPLACE applied** → tests re-run → iterate up to `max_reflections`

#### C. Per-Module Output
- `output.json` + `.done` sentinel

### After All Test Modules
- `trajectory.md` finalized
- Cost extracted (incremental + cumulative)

### ✅ Evaluation (Stage 3)
- Full test suite run — final results
- Save to `results_stage3.json`

---

## 5. Turn Types Captured

| Turn Role | When | Key Data |
|-----------|------|----------|
| `user` | Every prompt sent to LLM | `content` (assembled message) |
| `assistant` | Every LLM response | `content`, `thinking`, `thinking_tokens`, `prompt_tokens`, `completion_tokens`, `cache_hit_tokens`, `cache_write_tokens`, `cost`, `edit_error` |
| `tool_lint` | Lint runs (Stage 2) | `content` (lint output) |
| `tool_test` | Test runs (Stage 3) | `content` (test output, possibly summarized) |

Every turn also carries: `stage`, `module`, `turn_number`

---

## 6. Output Artifacts

### Per-Module (after each module completes)
- **`output.json`** — OpenHands event format: `SystemPromptEvent`, `MessageEvent`, `ActionEvent` (with `FileEditorAction` or `ThinkAction`), `ObservationEvent`, `FinishEvent`. Includes metrics: `stage_runtime_seconds`, `tool_calls`, tokens, cost.
- **`.done`** — crash recovery sentinel

### Per-Repo (after all modules in a stage)
- **`trajectory.md`** — human-readable Markdown: `# Trajectory: {repo}` → `## Stage N: {title}` → `### Module: {name}` → `#### Turn N — {Role}` with `<details>` blocks for thinking tokens
- **`output.jsonl`** — one JSON line per repo: `instance_id`, `attempt`, `git_patch`, `history` (all turns as dicts), `metrics`, `metadata`, `error`

### Per-Stage (by pipeline)
- **`results_stageN.json`** — evaluation results: per-repo pass/fail/runtime, cumulative cost

---

## 7. Watchdog (Wraps All Stages)

`watchdog_run()` polls every 15 seconds. Three kill conditions (checked in order):

1. **Absolute wall-time cap** → unconditional kill
2. **Hard timeout + inactive** → kill only if no log writes detected
3. **Inactivity timeout** → no `aider.log` or `agent_run.log` writes for N seconds

Returns exit code 124 on kill.

---

## 8. Pass@k Sampling (Optional)

When `--num-samples > 1`:
- Each sample gets its own branch (`base-run_1`, `base-run_2`, ...)
- Full 3-stage pipeline runs independently per sample
- `print_pass_at_k_summary()` calculates best-of-k pass rate across samples
