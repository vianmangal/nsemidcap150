from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RankConfig:
    mode: str = "turnover"
    top_n: int = 250

    @classmethod
    def from_env(cls) -> "RankConfig":
        mode = os.getenv("RANK_MODE", cls.mode).strip().lower()
        top_n_raw = os.getenv("TOP_N", str(cls.top_n)).strip()
        try:
            top_n = int(top_n_raw)
        except ValueError:
            top_n = cls.top_n
        return cls(mode=mode, top_n=top_n)

    def validate(self) -> None:
        if self.mode not in {"volume", "turnover"}:
            raise ValueError("RANK_MODE must be 'volume' or 'turnover'")
        if self.top_n <= 0:
            raise ValueError("TOP_N must be a positive integer")
