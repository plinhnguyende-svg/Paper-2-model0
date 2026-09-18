from __future__ import annotations

import pandas as pd


class Recorder:
    def __init__(self):
        self.period_rows: list[dict] = []

    def record(self, row: dict) -> None:
        self.period_rows.append(dict(row))

    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.period_rows)
