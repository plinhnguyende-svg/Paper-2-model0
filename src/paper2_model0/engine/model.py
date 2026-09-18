from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import numpy as np

from paper2_model0.config import SimulationConfig
from paper2_model0.domain.inventory import PerishableInventory
from paper2_model0.domain.shipment import Shipment, ShipmentManager
from paper2_model0.domain.observations import (
    ImporterReplenishmentObservation,
    RetailerObservation,
)
from paper2_model0.domain.scenario import ExogenousScenario
from paper2_model0.agents.retailer import Retailer
from paper2_model0.agents.importer import Importer
from paper2_model0.agents.exporter import Exporter
from paper2_model0.architectures import build_architecture
from paper2_model0.decision_architectures import RuleBasedDecisionArchitecture
from paper2_model0.engine.recorder import Recorder


@dataclass(frozen=True)
class RunResult:
    regime: str
    scenario_id: str
    period_df: object


class SupplyChainModel:
    TOL = 1e-8

    def __init__(
        self,
        config: SimulationConfig,
        regime: str,
        scenario: ExogenousScenario,
        architecture=None,
        decision_architecture=None,
    ):
        config.validate()
        if scenario.consumer_demand.shape[0] != config.simulation_horizon_days:
            raise ValueError("Scenario horizon does not match config.")
        self.config = config
        self.regime = regime
        self.scenario = scenario
        self.architecture = architecture or build_architecture(regime)
        self.decision_architecture = (
            decision_architecture or RuleBasedDecisionArchitecture(config)
        )
        self.shipments = ShipmentManager()
        self.recorder = Recorder()

        alpha = config.demand_forecast_smoothing_weight
        del alpha  # kept conceptually; policies get it from config

        self.retailers = [
            Retailer(
                retailer_id=f"R{r+1}",
                inventory=PerishableInventory(config.shelf_life_days),
                demand_forecast=config.retailer_mean_demand[r],
            )
            for r in range(3)
        ]
        self.importer = Importer(
            importer_id="B",
            inventory=PerishableInventory(config.shelf_life_days),
            downstream_order_forecast=sum(config.retailer_mean_demand),
        )
        p1, p2 = config.exporter_availability_probability
        self.exporters = [
            Exporter("E1", PerishableInventory(config.shelf_life_days), p1, p2),
            Exporter("E2", PerishableInventory(config.shelf_life_days), p2, p1),
        ]

        # Compatibility aliases for the frozen RuleBased benchmark. The engine
        # itself calls only observation-safe decision-architecture methods.
        self.retailer_policy = getattr(
            self.decision_architecture, "retailer_policy", None
        )
        self.importer_replenishment_policy = getattr(
            self.decision_architecture, "importer_replenishment_policy", None
        )
        self.importer_allocation_policy = getattr(
            self.decision_architecture, "importer_allocation_policy", None
        )
        self.exporter_readiness_policy = getattr(
            self.decision_architecture, "exporter_readiness_policy", None
        )

        self._initialize_inventory()
        self.initial_material = self._on_hand_total()
        self.cumulative_prepared = 0.0
        self.cumulative_consumed = 0.0
        self.cumulative_waste = 0.0

    def _initialize_inventory(self) -> None:
        c = self.config
        # Age-zero initial stocks near order-up-to targets.
        for r, retailer in enumerate(self.retailers):
            retailer.inventory.add((c.importer_to_retailer_lead_time_days + 1) * c.retailer_mean_demand[r], 0)
        aggregate_mean = sum(c.retailer_mean_demand)
        self.importer.inventory.add((c.exporter_to_importer_lead_time_days + 1) * aggregate_mean, 0)
        # Equal-share exporter stock benchmark.
        exporter_initial = 0.5 * aggregate_mean * (c.exporter_to_importer_lead_time_days + 1)
        for exporter in self.exporters:
            exporter.inventory.add(exporter_initial, 0)

    def _inventory_by_id(self, entity_id: str) -> PerishableInventory:
        if entity_id == "B":
            return self.importer.inventory
        for retailer in self.retailers:
            if retailer.retailer_id == entity_id:
                return retailer.inventory
        for exporter in self.exporters:
            if exporter.exporter_id == entity_id:
                return exporter.inventory
        raise KeyError(entity_id)

    def _on_hand_total(self) -> float:
        return float(
            self.importer.inventory.total_quantity()
            + sum(r.inventory.total_quantity() for r in self.retailers)
            + sum(e.inventory.total_quantity() for e in self.exporters)
        )

    def _receive_due_shipments(self, day: int) -> float:
        transit_waste = 0.0
        for shipment in self.shipments.arrivals_for_day(day):
            age = shipment.age_at_arrival()
            if age >= self.config.shelf_life_days:
                transit_waste += shipment.quantity
            else:
                rejected = self._inventory_by_id(shipment.destination_id).add(shipment.quantity, age)
                transit_waste += rejected
        return transit_waste

    def _dispatch_lots(self, origin_id: str, destination_id: str, requested: float,
                       lead_time: int, day: int) -> tuple[float, float]:
        inventory = self._inventory_by_id(origin_id)
        lots, unfulfilled = inventory.remove_fefo(requested)
        shipped = 0.0
        for lot in lots:
            shipped += lot.quantity
            self.shipments.schedule(Shipment(
                origin_id=origin_id,
                destination_id=destination_id,
                quantity=lot.quantity,
                age_at_dispatch=lot.age,
                dispatch_day=day,
                arrival_day=day + lead_time,
            ))
        return shipped, unfulfilled

    def _dispatch_importer_to_retailers(self, orders: tuple[float, float, float], day: int) -> tuple[float, float, float]:
        total_order = sum(orders)
        on_hand = self.importer.inventory.total_quantity()
        if total_order <= 0 or on_hand <= 0:
            requests = (0.0, 0.0, 0.0)
        elif total_order <= on_hand + self.TOL:
            requests = orders
        else:
            requests = tuple(on_hand * o / total_order for o in orders)

        shipped = []
        for retailer, request in zip(self.retailers, requests):
            qty, _ = self._dispatch_lots(
                "B",
                retailer.retailer_id,
                request,
                self.config.importer_to_retailer_lead_time_days,
                day,
            )
            shipped.append(qty)
        return tuple(shipped)  # type: ignore[return-value]

    def _age_all_inventory(self) -> float:
        waste = self.importer.age_inventory()
        waste += sum(r.age_inventory() for r in self.retailers)
        waste += sum(e.age_inventory() for e in self.exporters)
        return float(waste)

    def _assert_nonnegative(self) -> None:
        self.importer.inventory.assert_nonnegative()
        for x in self.retailers:
            x.inventory.assert_nonnegative()
        for x in self.exporters:
            x.inventory.assert_nonnegative()

    def _assert_material_balance(self) -> None:
        lhs = self.initial_material + self.cumulative_prepared
        rhs = (
            self._on_hand_total()
            + self.shipments.total_in_transit()
            + self.cumulative_consumed
            + self.cumulative_waste
        )
        if not np.isclose(lhs, rhs, atol=1e-7, rtol=1e-9):
            raise AssertionError(f"Material balance failure: lhs={lhs}, rhs={rhs}, diff={lhs-rhs}")

    def step(self, day: int) -> None:
        c = self.config
        transit_waste = self._receive_due_shipments(day)
        self.cumulative_waste += transit_waste

        current_demand = tuple(float(x) for x in self.scenario.consumer_demand[day])
        fulfilled = []
        lost = []
        for retailer, demand in zip(self.retailers, current_demand):
            f, l = retailer.serve_consumer_demand(demand)
            fulfilled.append(f)
            lost.append(l)
            self.cumulative_consumed += f

        retailer_orders = []
        for retailer, demand in zip(self.retailers, current_demand):
            obs = RetailerObservation(
                current_day=day,
                current_consumer_demand=demand,
                on_hand_inventory=retailer.inventory.total_quantity(),
                usable_pipeline_inventory=self.shipments.usable_pipeline_quantity(
                    retailer.retailer_id, c.shelf_life_days
                ),
                previous_forecast=retailer.demand_forecast,
            )
            action = self.decision_architecture.retailer_replenishment(obs)
            retailer.demand_forecast = action.updated_forecast
            retailer_orders.append(action.replenishment_order)
        retailer_orders_t = tuple(retailer_orders)  # type: ignore[assignment]

        retailer_shipments = self._dispatch_importer_to_retailers(retailer_orders_t, day)

        importer_replenishment_obs = ImporterReplenishmentObservation(
            current_day=day,
            current_retailer_orders=retailer_orders_t,
            previous_forecast=self.importer.downstream_order_forecast,
            on_hand_inventory=self.importer.inventory.total_quantity(),
            usable_pipeline_inventory=self.shipments.usable_pipeline_quantity(
                "B", c.shelf_life_days
            ),
        )
        importer_action = self.decision_architecture.importer_replenishment(
            importer_replenishment_obs
        )
        self.importer.downstream_order_forecast = importer_action.updated_forecast
        q = importer_action.procurement_requirement

        availability = tuple(bool(x) for x in self.scenario.exporter_availability[day])
        importer_obs = self.architecture.importer_observation(
            day=day,
            retailer_orders=retailer_orders_t,
            on_hand_inventory=self.importer.inventory.total_quantity(),
            usable_pipeline_inventory=self.shipments.usable_pipeline_quantity("B", c.shelf_life_days),
            availability=availability,
        )

        readiness_targets = []
        prepared = []
        observed_rival = []
        for i, exporter in enumerate(self.exporters):
            e_obs = self.architecture.exporter_observation(
                day=day,
                exporter_index=i,
                procurement_requirement=q,
                on_hand_inventory=exporter.inventory.total_quantity(),
                availability=availability,
                rival_availability_probability=exporter.known_rival_availability_probability,
            )
            action = self.decision_architecture.exporter_readiness(e_obs)
            exporter.prepare_fresh_units(action.prepared_quantity)
            self.cumulative_prepared += action.prepared_quantity
            readiness_targets.append(action.readiness_target)
            prepared.append(action.prepared_quantity)
            observed_rival.append(e_obs.rival_operational_availability)

        allocations = self.decision_architecture.importer_allocation(
            q, importer_obs
        )

        # Mechanism metrics are measured after readiness preparation but before fulfilment.
        # target_allocation_gap isolates information/decision matching; stock_allocation_gap
        # additionally captures carry-over inventory from prior periods.
        available_after_preparation = [e.inventory.total_quantity() for e in self.exporters]
        target_allocation_gap = [
            readiness_targets[i] - allocations[i]
            for i in range(2)
        ]
        stock_allocation_gap = [
            available_after_preparation[i] - allocations[i]
            for i in range(2)
        ]

        upstream_shipments = []
        for i, (exporter, allocation) in enumerate(zip(self.exporters, allocations)):
            request = allocation if availability[i] else 0.0
            qty, _ = self._dispatch_lots(
                exporter.exporter_id,
                "B",
                request,
                c.exporter_to_importer_lead_time_days,
                day,
            )
            exporter.cumulative_shipments += qty
            upstream_shipments.append(qty)

        on_hand_before_aging = self._on_hand_total()

        on_hand_waste = self._age_all_inventory()
        self.cumulative_waste += on_hand_waste

        row = {
            "day": day,
            "regime": self.regime,
            "scenario_id": self.scenario.scenario_id,
            "aggregate_consumer_demand": sum(current_demand),
            "aggregate_fulfilled_consumer_demand": sum(fulfilled),
            "aggregate_lost_sales": sum(lost),
            "aggregate_retailer_orders": sum(retailer_orders_t),
            "procurement_requirement": q,
            "availability_1": int(availability[0]),
            "availability_2": int(availability[1]),
            "observed_rival_1": observed_rival[0],
            "observed_rival_2": observed_rival[1],
            "readiness_target_1": readiness_targets[0],
            "readiness_target_2": readiness_targets[1],
            "prepared_quantity_1": prepared[0],
            "prepared_quantity_2": prepared[1],
            "available_stock_after_preparation_1": available_after_preparation[0],
            "available_stock_after_preparation_2": available_after_preparation[1],
            "allocation_1": allocations[0],
            "allocation_2": allocations[1],
            "upstream_shipment_1": upstream_shipments[0],
            "upstream_shipment_2": upstream_shipments[1],
            "retailer_shipment_1": retailer_shipments[0],
            "retailer_shipment_2": retailer_shipments[1],
            "retailer_shipment_3": retailer_shipments[2],
            "target_allocation_gap_1": target_allocation_gap[0],
            "target_allocation_gap_2": target_allocation_gap[1],
            "abs_target_allocation_gap_1": abs(target_allocation_gap[0]),
            "abs_target_allocation_gap_2": abs(target_allocation_gap[1]),
            "stock_allocation_gap_1": stock_allocation_gap[0],
            "stock_allocation_gap_2": stock_allocation_gap[1],
            "abs_stock_allocation_gap_1": abs(stock_allocation_gap[0]),
            "abs_stock_allocation_gap_2": abs(stock_allocation_gap[1]),
            "total_on_hand_inventory_pre_aging": on_hand_before_aging,
            "total_on_hand_inventory": self._on_hand_total(),
            "total_pipeline_inventory": self.shipments.total_in_transit(),
            "on_hand_waste": on_hand_waste,
            "transit_waste": transit_waste,
            "total_waste": on_hand_waste + transit_waste,
        }
        self.recorder.record(row)

        self._assert_nonnegative()
        self._assert_material_balance()

    def run(self):
        for day in range(self.config.simulation_horizon_days):
            self.step(day)
        return self.recorder.dataframe()
