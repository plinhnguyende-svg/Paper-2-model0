from paper2_model0.domain.shipment import Shipment, ShipmentManager


def test_shipment_age_and_pipeline():
    manager = ShipmentManager()
    s = Shipment("E1", "B", 5.0, 2, 0, 2)
    manager.schedule(s)
    assert s.age_at_arrival() == 4
    assert manager.total_in_transit() == 5.0
    assert manager.usable_pipeline_quantity("B", shelf_life_days=5) == 5.0
    assert manager.usable_pipeline_quantity("B", shelf_life_days=4) == 0.0
    due = manager.arrivals_for_day(2)
    assert due == [s]
    assert manager.total_in_transit() == 0.0
