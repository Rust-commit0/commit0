from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import docker.errors
import pytest

MODULE = "commit0.harness.docker_build_rust"


def _make_rust_spec(repo_image_key, setup_script, repo_dockerfile, platform):
    spec = MagicMock()
    spec.repo_image_key = repo_image_key
    spec.setup_script = setup_script
    spec.repo_dockerfile = repo_dockerfile
    spec.platform = platform
    return spec
