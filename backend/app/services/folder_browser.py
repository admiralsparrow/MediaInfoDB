from pathlib import Path

from app.config import settings


class FolderBrowser:
    def __init__(self):
        self.allowed_roots = [Path(r).resolve() for r in settings.allowed_roots_list]

    def is_path_allowed(self, path: str) -> bool:
        resolved = Path(path).resolve()
        return any(
            resolved == root or root in resolved.parents
            for root in self.allowed_roots
        )

    def list_directory(self, path: str) -> list[dict]:
        if not self.is_path_allowed(path):
            raise PermissionError("Path outside allowed roots")

        resolved = Path(path).resolve()
        if not resolved.is_dir():
            raise FileNotFoundError("Not a directory")

        entries = []
        try:
            for entry in sorted(resolved.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    has_children = False
                    try:
                        has_children = any(e.is_dir() for e in entry.iterdir())
                    except PermissionError:
                        pass
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "has_children": has_children,
                    })
        except PermissionError:
            pass

        return entries

    def get_roots(self) -> list[dict]:
        return [
            {"name": root.name or str(root), "path": str(root), "has_children": True}
            for root in self.allowed_roots
            if root.exists()
        ]


folder_browser = FolderBrowser()
