from pathlib import Path
import pandas as pd
from .analytics import validate


class DataStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self._data = self._load(self.path)

    def _load(self, path: Path) -> pd.DataFrame:
        return validate(pd.read_csv(path))

    @property
    def data(self) -> pd.DataFrame:
        return self._data.copy()

    def replace(self, content: bytes) -> int:
        import io
        candidate = validate(pd.read_csv(io.BytesIO(content)))
        self._data = candidate
        return len(candidate)
