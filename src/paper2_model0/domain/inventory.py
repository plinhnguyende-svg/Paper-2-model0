from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class RemovedLot:
    quantity: float
    age: int


class PerishableInventory:
    """Age-bucket inventory with FEFO removal.

    Buckets 0..L-1 are usable. At end-of-day aging, bucket L-1 expires.
    """

    def __init__(self, shelf_life_days: int, initial_buckets=None):
        if shelf_life_days < 1:
            raise ValueError("shelf_life_days must be >= 1")
        self.shelf_life_days = int(shelf_life_days)
        if initial_buckets is None:
            self.age_buckets = np.zeros(self.shelf_life_days, dtype=float)
        else:
            arr = np.asarray(initial_buckets, dtype=float)
            if arr.shape != (self.shelf_life_days,):
                raise ValueError("initial_buckets has wrong length")
            if np.any(arr < 0):
                raise ValueError("inventory cannot be negative")
            self.age_buckets = arr.copy()

    def total_quantity(self) -> float:
        return float(self.age_buckets.sum())

    def add(self, quantity: float, age: int = 0) -> float:
        """Add usable stock. Return quantity rejected as already expired."""
        quantity = float(quantity)
        age = int(age)
        if quantity < 0:
            raise ValueError("quantity must be nonnegative")
        if age < 0:
            raise ValueError("age must be nonnegative")
        if age >= self.shelf_life_days:
            return quantity
        self.age_buckets[age] += quantity
        return 0.0

    def remove_fefo(self, quantity: float) -> tuple[list[RemovedLot], float]:
        quantity = float(quantity)
        if quantity < 0:
            raise ValueError("quantity must be nonnegative")
        remaining = quantity
        removed: list[RemovedLot] = []
        for age in range(self.shelf_life_days - 1, -1, -1):
            if remaining <= 0:
                break
            available = float(self.age_buckets[age])
            take = min(available, remaining)
            if take > 0:
                self.age_buckets[age] -= take
                removed.append(RemovedLot(quantity=take, age=age))
                remaining -= take
        self._clip_tiny_negatives()
        return removed, float(remaining)

    def age_one_day(self) -> float:
        waste = float(self.age_buckets[-1])
        if self.shelf_life_days > 1:
            self.age_buckets[1:] = self.age_buckets[:-1]
        self.age_buckets[0] = 0.0
        return waste

    def assert_nonnegative(self, tolerance: float = 1e-10) -> None:
        minimum = float(self.age_buckets.min())
        if minimum < -tolerance:
            raise AssertionError(f"Negative inventory bucket detected: {minimum}")
        self._clip_tiny_negatives(tolerance)

    def _clip_tiny_negatives(self, tolerance: float = 1e-10) -> None:
        mask = (self.age_buckets < 0) & (self.age_buckets >= -tolerance)
        self.age_buckets[mask] = 0.0
