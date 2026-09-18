import numpy as np

from paper2_model0.domain.inventory import PerishableInventory


def test_v1_inventory_nonnegative_after_fefo():
    inv = PerishableInventory(4, [1.0, 2.0, 3.0, 4.0])
    lots, unfulfilled = inv.remove_fefo(8.0)
    assert unfulfilled == 0.0
    inv.assert_nonnegative()
    assert np.all(inv.age_buckets >= 0)
    assert sum(x.quantity for x in lots) == 8.0


def test_v3_shelf_life_expiration():
    inv = PerishableInventory(3)
    inv.add(10, age=2)
    waste = inv.age_one_day()
    assert waste == 10.0
    assert inv.total_quantity() == 0.0


def test_v8_fefo_correctness():
    inv = PerishableInventory(3, [5.0, 4.0, 3.0])
    lots, unfulfilled = inv.remove_fefo(6.0)
    assert unfulfilled == 0.0
    assert [(x.quantity, x.age) for x in lots] == [(3.0, 2), (3.0, 1)]
    assert np.allclose(inv.age_buckets, [5.0, 1.0, 0.0])
