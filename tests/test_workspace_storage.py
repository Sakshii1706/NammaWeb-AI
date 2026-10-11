from pathlib import Path

import pytest

from reach.storage.workspace_storage import WorkspaceStorage


def test_workspace_storage_creates_isolated_directories(tmp_path: Path):
    storage = WorkspaceStorage(
        project_root=tmp_path,
        workspace_id=1,
    )

    storage.ensure()

    assert storage.root_path == (
        tmp_path / "data" / "workspaces" / "1"
    )

    assert storage.documents_path == (
        tmp_path
        / "data"
        / "workspaces"
        / "1"
        / "documents"
    )

    assert storage.faiss_path == (
        tmp_path
        / "data"
        / "workspaces"
        / "1"
        / "faiss_index"
    )

    assert storage.documents_path.is_dir()
    assert storage.faiss_path.is_dir()


def test_different_workspaces_have_different_storage(tmp_path: Path):
    workspace_one = WorkspaceStorage(
        project_root=tmp_path,
        workspace_id=1,
    )

    workspace_two = WorkspaceStorage(
        project_root=tmp_path,
        workspace_id=2,
    )

    assert workspace_one.root_path != workspace_two.root_path
    assert workspace_one.documents_path != workspace_two.documents_path
    assert workspace_one.faiss_path != workspace_two.faiss_path


def test_workspace_id_must_be_positive(tmp_path: Path):
    with pytest.raises(ValueError):
        WorkspaceStorage(
            project_root=tmp_path,
            workspace_id=0,
        )

    with pytest.raises(ValueError):
        WorkspaceStorage(
            project_root=tmp_path,
            workspace_id=-1,
        )
from pathlib import Path

from reach.storage.workspace_storage import WorkspaceStorage


def test_workspace_storage_keeps_files_physically_isolated(
    tmp_path: Path,
):
    workspace_one = WorkspaceStorage(
        project_root=tmp_path,
        workspace_id=1,
    )

    workspace_two = WorkspaceStorage(
        project_root=tmp_path,
        workspace_id=2,
    )

    workspace_one.ensure()
    workspace_two.ensure()

    document_one = workspace_one.documents_path / "workspace-one.pdf"
    faiss_marker_one = workspace_one.faiss_path / "workspace-one.marker"

    document_one.write_text(
        "workspace one document",
        encoding="utf-8",
    )

    faiss_marker_one.write_text(
        "workspace one index",
        encoding="utf-8",
    )

    assert document_one.exists()
    assert faiss_marker_one.exists()

    assert not (
        workspace_two.documents_path
        / "workspace-one.pdf"
    ).exists()

    assert not (
        workspace_two.faiss_path
        / "workspace-one.marker"
    ).exists()
