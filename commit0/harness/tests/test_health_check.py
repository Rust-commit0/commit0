"""Tests for commit0.harness.health_check module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

MODULE = "commit0.harness.health_check"


class TestNormalizePipName:
    def test_lowercase(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("PyYAML") == "pyyaml"

    def test_strip_extras(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("requests[security]") == "requests"

    def test_strip_version_specifiers(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("numpy>=1.21") == "numpy"
        assert _normalize_pip_name("pandas<2.0") == "pandas"
        assert _normalize_pip_name("flask==2.0.1") == "flask"
        assert _normalize_pip_name("click!=7.0") == "click"
        assert _normalize_pip_name("tqdm~=4.62") == "tqdm"

    def test_strip_whitespace(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("  requests  ") == "requests"

    def test_combined(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("PyYAML[full]>=6.0") == "pyyaml"

    def test_empty_string(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("") == ""


class TestPipToImport:
    def test_known_mapping(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("pyyaml") == "yaml"
        assert pip_to_import("pillow") == "PIL"
        assert pip_to_import("scikit-learn") == "sklearn"
        assert pip_to_import("beautifulsoup4") == "bs4"
        assert pip_to_import("opencv-python") == "cv2"

    def test_heuristic_fallback(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("my-cool-package") == "my_cool_package"

    def test_case_insensitive(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("PyYAML") == "yaml"

    def test_with_extras(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("pyyaml[full]>=6.0") == "yaml"

    def test_unknown_package(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("some_plain_package") == "some_plain_package"


class TestDiscoverImportNames:
    @patch(f"{MODULE}.docker")
    def test_success(self, mock_docker):
        from commit0.harness.health_check import discover_import_names

        client = MagicMock()
        client.containers.run.return_value = b'{"numpy": ["numpy"], "pyyaml": ["yaml"]}'

        result = discover_import_names(client, "test-image:latest", ["numpy", "pyyaml"])
        assert result == {"numpy": ["numpy"], "pyyaml": ["yaml"]}

    @patch(f"{MODULE}.docker")
    def test_docker_failure_returns_none_values(self, mock_docker):
        from commit0.harness.health_check import discover_import_names

        client = MagicMock()
        client.containers.run.side_effect = Exception("Docker error")

        result = discover_import_names(client, "test-image:latest", ["numpy", "pandas"])
        assert result == {"numpy": None, "pandas": None}


class TestCheckImports:
    @patch(f"{MODULE}.discover_import_names")
    def test_skips_pytest_and_pip(self, mock_discover):
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        result = check_imports(
            client,
            "test-image:latest",
            ["pytest", "pip", "setuptools", "wheel", "coverage"],
        )
        assert result == (True, "No packages to check")
        mock_discover.assert_not_called()

    @patch(f"{MODULE}.discover_import_names")
    def test_all_imports_succeed(self, mock_discover):
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"numpy": ["numpy"]}
        client.containers.run.return_value = b""

        passed, msg = check_imports(client, "test-image:latest", ["numpy"])
        assert passed is True
        assert "1 packages importable" in msg

    @patch(f"{MODULE}.discover_import_names")
    def test_import_failure(self, mock_discover):
        import docker as _docker
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"badpkg": ["badpkg"]}
        client.containers.run.side_effect = _docker.errors.ContainerError(
            container=MagicMock(),
            exit_status=1,
            command="import",
            image="test",
            stderr=b"",
        )

        passed, msg = check_imports(client, "test-image:latest", ["badpkg"])
        assert passed is False
        assert "badpkg" in msg

    @patch(f"{MODULE}.discover_import_names")
    def test_fallback_to_static_map_when_discovery_returns_none(self, mock_discover):
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"pyyaml": None}
        client.containers.run.return_value = b""

        passed, msg = check_imports(client, "test-image:latest", ["pyyaml"])
        assert passed is True

    @patch(f"{MODULE}.discover_import_names")
    def test_empty_packages_list(self, mock_discover):
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        passed, msg = check_imports(client, "test-image:latest", [])
        assert passed is True
        mock_discover.assert_not_called()


class TestCheckPythonVersion:
    def test_version_match(self):
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.return_value = b"3.12"

        passed, msg = check_python_version(client, "test-image:latest", "3.12")
        assert passed is True
        assert "3.12" in msg

    def test_version_mismatch(self):
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.return_value = b"3.11"

        passed, msg = check_python_version(client, "test-image:latest", "3.12")
        assert passed is False
        assert "Expected" in msg

    def test_docker_error(self):
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.side_effect = Exception("Docker timeout")

        passed, msg = check_python_version(client, "test-image:latest", "3.12")
        assert passed is False
        assert "error" in msg.lower()


class TestRunHealthChecks:
    def test_no_checks_returns_empty(self):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(client, "test-image:latest")
        assert result == []

    @patch(f"{MODULE}.check_imports", return_value=(True, "All good"))
    def test_with_pip_packages(self, mock_check):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(client, "test-image:latest", pip_packages=["numpy"])
        assert len(result) == 1
        assert result[0] == (True, "imports", "All good")

    @patch(f"{MODULE}.check_python_version", return_value=(True, "Python 3.12"))
    def test_with_python_version(self, mock_check):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(client, "test-image:latest", python_version="3.12")
        assert len(result) == 1
        assert result[0] == (True, "python_version", "Python 3.12")

    @patch(f"{MODULE}.check_python_version", return_value=(True, "Python 3.12"))
    @patch(f"{MODULE}.check_imports", return_value=(True, "All good"))
    def test_both_checks(self, mock_imports, mock_version):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(
            client, "test-image:latest", pip_packages=["numpy"], python_version="3.12"
        )
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Expanded granular tests
# ---------------------------------------------------------------------------


class TestNormalizePipNameExpanded:
    """Additional edge-case coverage for _normalize_pip_name."""

    def test_multiple_version_operators(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("pkg>=1.0,<2.0") == "pkg"

    def test_tilde_equals(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("django~=3.2") == "django"

    def test_not_equals(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("foo!=1.0") == "foo"

    def test_extras_and_version_combined(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("requests[security,socks]>=2.0") == "requests"

    def test_name_with_dots(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("ruamel.yaml") == "ruamel.yaml"

    def test_name_with_underscores(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("typing_extensions") == "typing_extensions"

    def test_mixed_case_with_dash(self):
        from commit0.harness.health_check import _normalize_pip_name

        assert _normalize_pip_name("Scikit-Learn") == "scikit-learn"


class TestPipToImportExpanded:
    """Test all entries in _PIP_IMPORT_MAP and edge cases."""

    @pytest.mark.parametrize(
        "pip_name,expected",
        [
            ("python-dateutil", "dateutil"),
            ("python-dotenv", "dotenv"),
            ("attrs", "attr"),
            ("pyjwt", "jwt"),
            ("python-jose", "jose"),
            ("python-multipart", "multipart"),
            ("msgpack-python", "msgpack"),
            ("biscuit-python", "biscuit_auth"),
            ("google-cloud-storage", "google.cloud.storage"),
            ("google-auth", "google.auth"),
            ("protobuf", "google.protobuf"),
            ("grpcio", "grpc"),
            ("opencv-python-headless", "cv2"),
            ("ruamel.yaml", "ruamel.yaml"),
            ("importlib-metadata", "importlib_metadata"),
            ("typing-extensions", "typing_extensions"),
        ],
    )
    def test_all_pip_import_map_entries(self, pip_name, expected):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import(pip_name) == expected

    def test_heuristic_replaces_all_dashes(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("my-cool-long-package") == "my_cool_long_package"

    def test_empty_string_returns_empty(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("") == ""

    def test_already_underscore(self):
        from commit0.harness.health_check import pip_to_import

        assert pip_to_import("some_package") == "some_package"


class TestDiscoverImportNamesExpanded:
    """Edge cases for discover_import_names."""

    @patch(f"{MODULE}.docker")
    def test_json_with_multiple_modules(self, mock_docker):
        from commit0.harness.health_check import discover_import_names

        client = MagicMock()
        client.containers.run.return_value = (
            b'{"google-cloud-storage": ["google.cloud.storage", "google.cloud"]}'
        )

        result = discover_import_names(
            client, "test-image:latest", ["google-cloud-storage"]
        )
        assert result["google-cloud-storage"] == [
            "google.cloud.storage",
            "google.cloud",
        ]

    @patch(f"{MODULE}.docker")
    def test_invalid_json_returns_none_values(self, mock_docker):
        from commit0.harness.health_check import discover_import_names

        client = MagicMock()
        client.containers.run.return_value = b"not valid json"

        result = discover_import_names(client, "test-image:latest", ["numpy"])
        assert result == {"numpy": None}

    @patch(f"{MODULE}.docker")
    def test_empty_pip_list(self, mock_docker):
        from commit0.harness.health_check import discover_import_names

        client = MagicMock()
        client.containers.run.return_value = b"{}"

        result = discover_import_names(client, "test-image:latest", [])
        assert result == {}


class TestCheckImportsExpanded:
    """Additional edge-case coverage for check_imports."""

    @patch(f"{MODULE}.discover_import_names")
    def test_noncritical_exception_logs_and_fails(self, mock_discover):
        """Line 138-140: non-ContainerError exception path."""
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"numpy": ["numpy"]}
        # Generic Exception (not ContainerError) - non-critical path
        client.containers.run.side_effect = RuntimeError("network glitch")

        passed, msg = check_imports(client, "test-image:latest", ["numpy"])
        assert passed is False
        assert "numpy" in msg
        assert "error:" in msg

    @patch(f"{MODULE}.discover_import_names")
    def test_multiple_packages_partial_failure(self, mock_discover):
        """Some packages import fine, others fail."""
        import docker as _docker
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"numpy": ["numpy"], "badpkg": ["badpkg"]}

        def selective_run(image, cmd, **kwargs):
            if "badpkg" in cmd:
                raise _docker.errors.ContainerError(
                    container=MagicMock(),
                    exit_status=1,
                    command="import",
                    image="test",
                    stderr=b"",
                )
            return b""

        client.containers.run.side_effect = selective_run

        passed, msg = check_imports(client, "test-image:latest", ["numpy", "badpkg"])
        assert passed is False
        assert "badpkg" in msg

    @patch(f"{MODULE}.discover_import_names")
    def test_coverage_prefixed_packages_skipped(self, mock_discover):
        """Packages starting with skip prefixes are excluded."""
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        result = check_imports(
            client,
            "test-image:latest",
            ["pytest-cov", "coverage-badge", "pip-tools", "setuptools-scm"],
        )
        assert result == (True, "No packages to check")
        mock_discover.assert_not_called()

    @patch(f"{MODULE}.discover_import_names")
    def test_dotted_module_uses_top_level(self, mock_discover):
        """google.cloud.storage should import as 'google'."""
        from commit0.harness.health_check import check_imports

        client = MagicMock()
        mock_discover.return_value = {"google-cloud-storage": ["google.cloud.storage"]}
        client.containers.run.return_value = b""

        passed, msg = check_imports(
            client, "test-image:latest", ["google-cloud-storage"]
        )
        assert passed is True
        # Verify the import cmd used top-level module 'google'
        cmd_arg = client.containers.run.call_args[0][1]
        assert "import google" in cmd_arg


class TestCheckPythonVersionExpanded:
    """Extra edge cases for check_python_version."""

    def test_whitespace_stripped_from_output(self):
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.return_value = b"  3.12  \n"

        passed, msg = check_python_version(client, "test-image:latest", "3.12")
        assert passed is True

    def test_partial_version_match(self):
        """3.12 should NOT match 3.121."""
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.return_value = b"3.121"

        passed, msg = check_python_version(client, "test-image:latest", "3.12")
        assert passed is False

    def test_version_with_newline(self):
        from commit0.harness.health_check import check_python_version

        client = MagicMock()
        client.containers.run.return_value = b"3.11\n"

        passed, msg = check_python_version(client, "test-image:latest", "3.11")
        assert passed is True


class TestRunHealthChecksExpanded:
    """Additional orchestration tests."""

    @patch(f"{MODULE}.check_python_version", return_value=(False, "Wrong"))
    @patch(f"{MODULE}.check_imports", return_value=(False, "Import fail"))
    def test_failed_checks_included(self, mock_imports, mock_version):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(
            client,
            "test-image:latest",
            pip_packages=["numpy"],
            python_version="3.12",
        )
        assert len(result) == 2
        assert result[0][0] is False
        assert result[1][0] is False

    @patch(f"{MODULE}.check_imports")
    def test_empty_pip_packages_list_skips_check(self, mock_check):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(client, "test-image:latest", pip_packages=[])
        assert result == []
        mock_check.assert_not_called()

    @patch(f"{MODULE}.check_python_version")
    def test_none_python_version_skips_check(self, mock_check):
        from commit0.harness.health_check import run_health_checks

        client = MagicMock()
        result = run_health_checks(client, "test-image:latest", python_version=None)
        assert result == []
        mock_check.assert_not_called()
