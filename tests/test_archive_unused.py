"""Tests for archive_unused tool."""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from tools.archive_unused import (
    ImportAnalyzer,
    DeadCodeDetector,
    FileArchiver,
)


class TestImportAnalyzer:
    """Tests for ImportAnalyzer."""

    def test_simple_import(self):
        """Test analyzing simple import."""
        code = "import os\nimport sys"
        import ast

        tree = ast.parse(code)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        assert "os" in analyzer.imports
        assert "sys" in analyzer.imports

    def test_from_import(self):
        """Test analyzing from import."""
        code = "from pathlib import Path\nfrom typing import List"
        import ast

        tree = ast.parse(code)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        assert "pathlib" in analyzer.imports
        assert "typing" in analyzer.imports

    def test_nested_import(self):
        """Test analyzing nested imports."""
        code = "from src.utils.config import ConfigManager"
        import ast

        tree = ast.parse(code)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        assert "src" in analyzer.imports


class TestDeadCodeDetector:
    """Tests for DeadCodeDetector."""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create structure
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "__init__.py").write_text("")
        (temp_dir / "src" / "main.py").write_text(
            "from src.utils import helper\n\nif __name__ == '__main__':\n    pass"
        )
        (temp_dir / "src" / "utils").mkdir()
        (temp_dir / "src" / "utils" / "__init__.py").write_text("")
        (temp_dir / "src" / "utils" / "helper.py").write_text("def help():\n    pass")

        # Create truly isolated unused file in different directory
        (temp_dir / "old_code").mkdir()
        (temp_dir / "old_code" / "deprecated.py").write_text("# This file is not imported")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_find_python_files(self, temp_repo):
        """Test finding Python files."""
        detector = DeadCodeDetector(temp_repo)
        files = detector.find_python_files()

        # Should find main.py, helper.py, deprecated.py (not __init__.py)
        file_names = {f.name for f in files}
        assert "main.py" in file_names
        assert "helper.py" in file_names
        assert "deprecated.py" in file_names
        assert "__init__.py" not in file_names  # Excluded

    def test_find_entrypoints(self, temp_repo):
        """Test finding entrypoint files."""
        detector = DeadCodeDetector(temp_repo)
        files = detector.find_python_files()
        entrypoints = detector.find_entrypoints(files)

        # main.py has if __name__ == "__main__"
        entrypoint_names = {f.name for f in entrypoints}
        assert "main.py" in entrypoint_names

    def test_build_import_graph(self, temp_repo):
        """Test building import graph."""
        detector = DeadCodeDetector(temp_repo)
        files = detector.find_python_files()
        graph = detector.build_import_graph(files)

        # main.py should import src
        main_py = next(f for f in files if f.name == "main.py")
        assert "src" in graph[main_py]

    def test_find_unused_files(self, temp_repo):
        """Test finding unused files."""
        detector = DeadCodeDetector(temp_repo)
        unused = detector.find_unused_files()

        # deprecated.py should be detected
        unused_names = {f.name for f in unused}
        assert "deprecated.py" in unused_names

        # main.py and helper.py should not be unused
        assert "main.py" not in unused_names
        assert "helper.py" not in unused_names

    def test_generate_report(self, temp_repo):
        """Test report generation."""
        detector = DeadCodeDetector(temp_repo)
        unused = detector.find_unused_files()
        report = detector.generate_report(unused)

        assert "deprecated.py" in report
        assert "Dead Code Detection Report" in report


class TestFileArchiver:
    """Tests for FileArchiver."""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create structure
        (temp_dir / "src").mkdir()
        test_file = temp_dir / "src" / "unused.py"
        test_file.write_text("# Unused file content\n")

        yield temp_dir, test_file

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_create_archive_dir(self, temp_repo):
        """Test archive directory creation."""
        temp_dir, _ = temp_repo
        archiver = FileArchiver(temp_dir, version="1.0.0")

        archive_dir = archiver.create_archive_dir()

        assert archive_dir.exists()
        assert archive_dir.is_dir()
        assert "ARCHIVE" in str(archive_dir)
        assert "v1.0.0" in str(archive_dir)

    def test_compute_file_hash(self, temp_repo):
        """Test file hash computation."""
        temp_dir, test_file = temp_repo
        archiver = FileArchiver(temp_dir)

        hash1 = archiver.compute_file_hash(test_file)
        assert len(hash1) == 64  # SHA256 hex digest

        # Should be consistent
        hash2 = archiver.compute_file_hash(test_file)
        assert hash1 == hash2

    def test_archive_files_dry_run(self, temp_repo):
        """Test dry run mode."""
        temp_dir, test_file = temp_repo
        archiver = FileArchiver(temp_dir)

        result = archiver.archive_files([test_file], dry_run=True)

        assert result["dry_run"] is True
        assert result["file_count"] == 1
        assert test_file.exists()  # File should not be moved

    def test_archive_files(self, temp_repo):
        """Test actual file archiving."""
        temp_dir, test_file = temp_repo
        archiver = FileArchiver(temp_dir, version="1.0.0")

        manifest = archiver.archive_files([test_file], dry_run=False)

        # Check manifest
        assert "version" in manifest
        assert "timestamp" in manifest
        assert len(manifest["archived_files"]) == 1

        file_info = manifest["archived_files"][0]
        assert "src/unused.py" in file_info["original_path"]
        assert file_info["hash"]

        # File should be moved
        assert not test_file.exists()

        # File should exist in archive
        archive_path = temp_dir / file_info["archive_path"]
        assert archive_path.exists()

    def test_undo_archive(self, temp_repo):
        """Test archive restoration."""
        temp_dir, test_file = temp_repo
        archiver = FileArchiver(temp_dir, version="1.0.0")

        # Archive file
        manifest = archiver.archive_files([test_file], dry_run=False)
        assert not test_file.exists()

        # Find manifest file
        archive_dir = None
        for item in (temp_dir / "ARCHIVE").iterdir():
            if item.is_dir():
                archive_dir = item
                break

        manifest_path = archive_dir / "manifest.json"
        assert manifest_path.exists()

        # Restore
        success = archiver.undo_archive(manifest_path)
        assert success

        # File should be restored
        assert test_file.exists()
        content = test_file.read_text()
        assert "Unused file content" in content

    def test_archive_empty_list(self, temp_repo):
        """Test archiving empty list."""
        temp_dir, _ = temp_repo
        archiver = FileArchiver(temp_dir)

        result = archiver.archive_files([])
        assert result == {}
