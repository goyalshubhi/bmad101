from abc import ABC, abstractmethod
from typing import BinaryIO

import pandas as pd


class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, file: BinaryIO) -> pd.DataFrame:
        pass

    @abstractmethod
    def detect_schema(self, df: pd.DataFrame) -> dict:
        pass
