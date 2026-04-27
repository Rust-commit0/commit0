"""Exhaustive unit tests for commit0.harness.build_rust."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

MODULE = "commit0.harness.build_rust"

from commit0.harness.build_rust import _load_datasets, RUST_DATASET_GLOB


# ===== RUST_DATASET_GLOB constant =====
class TestRustDatasetGlob:
    def test_value(self):
        assert RUST_DATASET_GLOB == "*_rust_dataset.json"

    def test_is_string(self):
        assert isinstance(RUST_DATASET_GLOB, str)

    def test_ends_with_json(self):
        assert RUST_DATASET_GLOB.endswith(".json")


# ===== _load_datasets =====
class TestLoadDatasetsSingleFile:
    def test_loads_list_json(self, tmp_path):
        data = [{"repo": "Rust-commit0/taffy", "instance_id": "t1"}]
        f = tmp_path / "test_rust_dataset.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert len(result) == 1
        assert result[0]["repo"] == "Rust-commit0/taffy"

    def test_loads_dict_json_converts_to_list(self, tmp_path):
        data = {"taffy": {"repo": "Rust-commit0/taffy"}, "bon": {"repo": "Rust-commit0/bon"}}
        f = tmp_path / "test_rust_dataset.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert len(result) == 2
        repos = [r["repo"] for r in result]
        assert "Rust-commit0/taffy" in repos
        assert "Rust-commit0/bon" in repos

    def test_empty_list(self, tmp_path):
        f = tmp_path / "test_rust_dataset.json"
        f.write_text("[]")
        result = _load_datasets(f)
        assert result == []

    def test_empty_dict(self, tmp_path):
        f = tmp_path / "test_rust_dataset.json"
        f.write_text("{}")
        result = _load_datasets(f)
        assert result == []

    def test_single_item_list(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps([{"id": 1}]))
        result = _load_datasets(f)
        assert len(result) == 1

    def test_preserves_all_fields(self, tmp_path):
        data = [{"repo": "r", "instance_id": "i", "base_commit": "abc", "extra": True}]
        f = tmp_path / "d.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert result[0]["extra"] is True
        assert result[0]["base_commit"] == "abc"

    def test_large_dataset(self, tmp_path):
        data = [{"repo": f"org/repo{i}"} for i in range(100)]
        f = tmp_path / "big.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert len(result) == 100


class TestLoadDatasetsDirectory:
    def test_loads_from_directory(self, tmp_path):
        data1 = [{"repo": "org/a"}]
        data2 = [{"repo": "org/b"}]
        (tmp_path / "a_rust_dataset.json").write_text(json.dumps(data1))
        (tmp_path / "b_rust_dataset.json").write_text(json.dumps(data2))
        result = _load_datasets(tmp_path)
        assert len(result) == 2
        repos = [r["repo"] for r in result]
        assert "org/a" in repos
        assert "org/b" in repos

    def test_empty_directory_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            _load_datasets(tmp_path)

    def test_ignores_non_matching_files(self, tmp_path):
        (tmp_path / "a_rust_dataset.json").write_text('[{"repo":"org/a"}]')
        (tmp_path / "other.json").write_text('[{"repo":"org/b"}]')
        result = _load_datasets(tmp_path)
        assert len(result) == 1
        assert result[0]["repo"] == "org/a"

    def test_merges_multiple_files(self, tmp_path):
        for i in range(5):
            (tmp_path / f"set{i}_rust_dataset.json").write_text(
                json.dumps([{"repo": f"org/repo{i}"}])
            )
        result = _load_datasets(tmp_path)
        assert len(result) == 5

    def test_dict_files_in_directory(self, tmp_path):
        (tmp_path / "x_rust_dataset.json").write_text(
            json.dumps({"k1": {"repo": "org/a"}, "k2": {"repo": "org/b"}})
        )
        result = _load_datasets(tmp_path)
        assert len(result) == 2

    def test_mixed_list_and_dict_files(self, tmp_path):
        (tmp_path / "a_rust_dataset.json").write_text(json.dumps([{"repo": "org/a"}]))
        (tmp_path / "b_rust_dataset.json").write_text(json.dumps({"k": {"repo": "org/b"}}))
        result = _load_datasets(tmp_path)
        assert len(result) == 2


class TestLoadDatasetsNonexistent:
    def test_nonexistent_path_exits(self):
        with pytest.raises(SystemExit):
            _load_datasets(Path("/nonexistent/path/to/file.json"))

    def test_nonexistent_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            _load_datasets(tmp_path / "missing.json")


class TestLoadDatasetsEdgeCases:
    def test_nested_data_preserved(self, tmp_path):
        data = [{"repo": "r", "setup": {"pre_install": ["apt-get update"]}}]
        f = tmp_path / "d.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert result[0]["setup"]["pre_install"] == ["apt-get update"]

    def test_unicode_content(self, tmp_path):
        data = [{"repo": "org/repo", "desc": "unicode: \u00e9\u00e8\u00ea"}]
        f = tmp_path / "d.json"
        f.write_text(json.dumps(data))
        result = _load_datasets(f)
        assert "\u00e9" in result[0]["desc"]

    def test_invalid_json_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            _load_datasets(f)

    def test_sorted_file_order_in_directory(self, tmp_path):
        (tmp_path / "z_rust_dataset.json").write_text(json.dumps([{"order": 2}]))
        (tmp_path / "a_rust_dataset.json").write_text(json.dumps([{"order": 1}]))
        result = _load_datasets(tmp_path)
        assert result[0]["order"] == 1
        assert result[1]["order"] == 2


# ===== main =====
from commit0.harness.build_rust import main


class TestMain:
    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_success(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}]
        mock_build.return_value = (["img1"], [])
        main("/path/to/data.json")
        mock_docker.assert_called_once()
        mock_build.assert_called_once()

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_failed_builds_exit(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}]
        mock_build.return_value = ([], ["org/a"])
        with pytest.raises(SystemExit):
            main("/path/to/data.json")

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_passes_num_workers(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}]
        mock_build.return_value = (["img"], [])
        main("/path/to/data.json", num_workers=8)
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["max_workers"] == 8

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_passes_verbose(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}]
        mock_build.return_value = (["img"], [])
        main("/path/to/data.json", verbose=2)
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["verbose"] == 2

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_default_workers(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}]
        mock_build.return_value = (["img"], [])
        main("/path/to/data.json")
        call_kwargs = mock_build.call_args[1]
        assert call_kwargs["max_workers"] == 4

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_empty_dataset(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = []
        mock_build.return_value = ([], [])
        main("/path/to/data.json")
        mock_build.assert_called_once()

    @patch(f"{MODULE}.docker.from_env", side_effect=Exception("Docker not running"))
    @patch(f"{MODULE}._load_datasets")
    def test_docker_not_available(self, mock_load, mock_docker):
        mock_load.return_value = [{"repo": "org/a"}]
        with pytest.raises(Exception, match="Docker not running"):
            main("/path/to/data.json")

    @patch(f"{MODULE}.build_rust_repo_images")
    @patch(f"{MODULE}.docker.from_env")
    @patch(f"{MODULE}._load_datasets")
    def test_partial_failure(self, mock_load, mock_docker, mock_build):
        mock_load.return_value = [{"repo": "org/a"}, {"repo": "org/b"}]
        mock_build.return_value = (["img_a"], ["org/b"])
        with pytest.raises(SystemExit):
            main("/path")
