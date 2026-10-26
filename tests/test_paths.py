import sys

from autodrive_editor.paths import PROJECT_ROOT, local_projects_directory


def test_local_projects_directory_is_in_repository():
    assert local_projects_directory() == PROJECT_ROOT / "local_projects"


def test_local_projects_directory_is_in_user_data_when_bundled(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("AUTODRIVE_EDITOR_DATA_DIR", str(tmp_path))

    assert local_projects_directory() == tmp_path / "projects"
