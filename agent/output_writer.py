"""Write structured output.jsonl for benchmark evaluation."""

import json
from pathlib import Path
from typing import Any


def write_output_jsonl(
    output_path: Path,
    instance_id: str,
    instruction: str,
    git_patch: str,
    events: list[dict],
    metrics: dict,
    metadata: dict,
    error: str | None = None,
    attempt: int = 1,
) -> None:
    """Write a single output.jsonl line in the target format.

    Parameters
    ----------
    output_path : Path
        Where to write (appends one JSON line).
    instance_id : str
        E.g., "commit-0/itsdangerous".
    instruction : str
        The original user instruction/prompt.
    git_patch : str
        Git diff of all changes made.
    events : list[dict]
        Conversation history from ThinkingCapture.to_history().
    metrics : dict
        Aggregated metrics from ThinkingCapture.get_metrics().
    metadata : dict
        Run metadata (model, dataset, etc.).
    error : str | None
        Error message if run failed, None otherwise.
    attempt : int
        Attempt number (for multi-sample runs).
    """
    record = {
        "instance_id": instance_id,
        "attempt": attempt,
        "test_result": {
            "git_patch": git_patch,
        },
        "instruction": instruction,
        "metadata": metadata,
        "history": events,
        "metrics": metrics,
        "error": error,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def extract_git_patch(repo_path: str, base_commit: str) -> str:
    """Extract the git diff between current state and base_commit.

    Parameters
    ----------
    repo_path : str
        Path to the git repository.
    base_commit : str
        The base commit hash to diff against.

    Returns
    -------
    str
        The git diff as a string, or empty string on failure.
    """
    import git

    repo = git.Repo(repo_path)
    try:
        return repo.git.diff(base_commit, "--", ".")
    except Exception:
        return ""


def build_metadata(
    model_name: str,
    dataset_path: str,
    max_iterations: int,
    **extra: Any,
) -> dict:
    """Build the metadata object for output.jsonl.

    Parameters
    ----------
    model_name : str
        The LLM model identifier.
    dataset_path : str
        Path or name of the dataset used.
    max_iterations : int
        Max agent iterations configured.
    **extra
        Additional metadata fields.

    Returns
    -------
    dict
        Metadata dictionary for output.jsonl.
    """
    return {
        "llm": {
            "model": model_name,
            **{k: v for k, v in extra.items() if k.startswith("llm_")},
        },
        "dataset": dataset_path,
        "max_iterations": max_iterations,
    }
