import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.folder_browser import FolderBrowser


@pytest.fixture
def media_tree(tmp_path):
    """Create a directory tree for testing."""
    movies = tmp_path / "media" / "movies"
    movies.mkdir(parents=True)
    (movies / "Movie1").mkdir()
    (movies / "Movie2").mkdir()
    (movies / ".hidden").mkdir()

    tv = tmp_path / "media" / "tv"
    tv.mkdir(parents=True)
    (tv / "Show1").mkdir()
    (tv / "Show1" / "Season 1").mkdir()

    return tmp_path / "media"


@pytest.fixture
def browser(media_tree):
    with patch("app.services.folder_browser.settings") as mock_settings:
        mock_settings.allowed_roots_list = [str(media_tree)]
        return FolderBrowser()


class TestIsPathAllowed:
    def test_allowed_root(self, browser, media_tree):
        assert browser.is_path_allowed(str(media_tree)) is True

    def test_allowed_subdir(self, browser, media_tree):
        assert browser.is_path_allowed(str(media_tree / "movies")) is True

    def test_disallowed_path(self, browser, tmp_path):
        assert browser.is_path_allowed(str(tmp_path / "secret")) is False

    def test_parent_of_root_disallowed(self, browser, media_tree):
        assert browser.is_path_allowed(str(media_tree.parent)) is False


class TestListDirectory:
    def test_lists_subdirs(self, browser, media_tree):
        entries = browser.list_directory(str(media_tree / "movies"))
        names = [e["name"] for e in entries]
        assert "Movie1" in names
        assert "Movie2" in names

    def test_excludes_hidden_dirs(self, browser, media_tree):
        entries = browser.list_directory(str(media_tree / "movies"))
        names = [e["name"] for e in entries]
        assert ".hidden" not in names

    def test_has_children_flag(self, browser, media_tree):
        entries = browser.list_directory(str(media_tree / "tv"))
        show_entry = next(e for e in entries if e["name"] == "Show1")
        assert show_entry["has_children"] is True

    def test_sorted_output(self, browser, media_tree):
        entries = browser.list_directory(str(media_tree / "movies"))
        names = [e["name"] for e in entries]
        assert names == sorted(names)

    def test_disallowed_path_raises(self, browser, tmp_path):
        with pytest.raises(PermissionError):
            browser.list_directory(str(tmp_path / "secret"))

    def test_nonexistent_dir_raises(self, browser, media_tree):
        with pytest.raises(FileNotFoundError):
            browser.list_directory(str(media_tree / "nonexistent"))


class TestGetRoots:
    def test_returns_existing_roots(self, browser, media_tree):
        roots = browser.get_roots()
        assert len(roots) == 1
        assert roots[0]["path"] == str(media_tree)
        assert roots[0]["has_children"] is True

    def test_excludes_nonexistent_roots(self, tmp_path):
        with patch("app.services.folder_browser.settings") as mock_settings:
            mock_settings.allowed_roots_list = [str(tmp_path / "does_not_exist")]
            browser = FolderBrowser()
            roots = browser.get_roots()
            assert len(roots) == 0

    def test_multiple_roots(self, tmp_path):
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()
        with patch("app.services.folder_browser.settings") as mock_settings:
            mock_settings.allowed_roots_list = [str(root1), str(root2)]
            browser = FolderBrowser()
            roots = browser.get_roots()
            assert len(roots) == 2
