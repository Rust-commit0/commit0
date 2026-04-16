import importlib.util
import os
from types import ModuleType

_LEGACY_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "dockerfiles.py")


def _load_legacy_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "commit0.harness.dockerfiles_legacy", os.path.abspath(_LEGACY_PATH)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_legacy_module()

_DOCKERFILE_BASE: str = _mod._DOCKERFILE_BASE
_DOCKERFILE_REPO: str = _mod._DOCKERFILE_REPO
get_dockerfile_base = _mod.get_dockerfile_base
get_dockerfile_repo = _mod.get_dockerfile_repo


class TestGetDockerfileBase:
    def test_returns_string(self) -> None:
        result = get_dockerfile_base()
        assert isinstance(result, str)

    def test_contains_from_ubuntu(self) -> None:
        result = get_dockerfile_base()
        assert "FROM ubuntu:22.04" in result

    def test_contains_python3(self) -> None:
        result = get_dockerfile_base()
        assert "python3" in result

    def test_contains_git_install(self) -> None:
        result = get_dockerfile_base()
        assert "git" in result

    def test_contains_mitm_ca_handling(self) -> None:
        result = get_dockerfile_base()
        assert "mitm-ca" in result.lower() or "MITM" in result

    def test_contains_uv_shim(self) -> None:
        result = get_dockerfile_base()
        assert "uv" in result

    def test_returns_same_as_constant(self) -> None:
        assert get_dockerfile_base() is _DOCKERFILE_BASE

    def test_contains_proxy_args(self) -> None:
        result = get_dockerfile_base()
        assert "http_proxy" in result
        assert "https_proxy" in result


class TestGetDockerfileRepo:
    def test_returns_string(self) -> None:
        result = get_dockerfile_repo()
        assert isinstance(result, str)

    def test_contains_from_commit0_base(self) -> None:
        result = get_dockerfile_repo()
        assert "FROM commit0.base:latest" in result

    def test_contains_setup_sh(self) -> None:
        result = get_dockerfile_repo()
        assert "setup.sh" in result

    def test_contains_workdir_testbed(self) -> None:
        result = get_dockerfile_repo()
        assert "WORKDIR /testbed/" in result

    def test_contains_proxy_args(self) -> None:
        result = get_dockerfile_repo()
        assert "http_proxy" in result

    def test_contains_bashrc_activation(self) -> None:
        result = get_dockerfile_repo()
        assert ".bashrc" in result

    def test_returns_same_as_constant(self) -> None:
        assert get_dockerfile_repo() is _DOCKERFILE_REPO


class TestDockerfileConstants:
    def test_base_is_nonempty_string(self) -> None:
        assert isinstance(_DOCKERFILE_BASE, str)
        assert len(_DOCKERFILE_BASE) > 100

    def test_repo_is_nonempty_string(self) -> None:
        assert isinstance(_DOCKERFILE_REPO, str)
        assert len(_DOCKERFILE_REPO) > 50
