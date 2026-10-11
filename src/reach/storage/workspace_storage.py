from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceStorage:
    """
    Resolves and manages physical storage for one workspace.

    Each workspace gets its own document directory and FAISS index
    directory under:

        data/workspaces/<workspace_id>/
    """

    project_root: Path
    workspace_id: int

    def __post_init__(self) -> None:
        if self.workspace_id <= 0:
            raise ValueError("workspace_id must be a positive integer.")

    @property
    def root_path(self) -> Path:
        return (
            self.project_root
            / "data"
            / "workspaces"
            / str(self.workspace_id)
        )

    @property
    def documents_path(self) -> Path:
        return self.root_path / "documents"

    @property
    def faiss_path(self) -> Path:
        return self.root_path / "faiss_index"

    def ensure(self) -> None:
        """Create the workspace storage directories if needed."""
        self.documents_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.faiss_path.mkdir(
            parents=True,
            exist_ok=True,
        )
