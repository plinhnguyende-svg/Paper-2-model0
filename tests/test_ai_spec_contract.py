from pathlib import Path

import yaml


SPEC_PATH = Path("experiments/ai_decision_architecture_spec_v0.1.yaml")
FROZEN_FIREWALL_COMMIT = "a1c0b15163d05fd4b02ccdcb1fa2843a421a07d3"


def _load_spec():
    with SPEC_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ai_spec_is_pretraining_and_pinned_to_frozen_firewall():
    spec = _load_spec()
    assert spec["status"] == "draft_pre_training"
    assert spec["frozen_firewall_base_commit"] == FROZEN_FIREWALL_COMMIT
    assert spec["no_training_gate"]["training_allowed_before_spec_merge"] is False
    assert spec["no_training_gate"]["implementation_branch_must_start_from_locked_spec_commit"] is True


def test_ai_spec_preserves_factorial_identification_and_local_information():
    spec = _load_spec()
    assert spec["factorial_design"]["information_regimes"] == ["N", "S", "F"]
    assert spec["factorial_design"]["decision_architectures"] == ["RuleBased", "AI"]
    assert spec["factorial_design"]["node_level_ablations_confirmatory"] is False
    assert spec["ai_algorithm"]["centralized_critic"] is False
    assert spec["ai_algorithm"]["recurrent"] is False
    assert spec["ai_algorithm"]["parameter_sharing"] is False
    assert spec["actor_instances"]["shared_mutable_policy_instances_allowed"] is False
    assert spec["actor_instances"]["ai_controls_importer_allocation"] is False
    assert spec["observation_encoding"]["include_regime_label"] is False
    assert spec["observation_encoding"]["include_current_day"] is False
    assert spec["observation_encoding"]["identical_input_dimension_across_regimes"] is True


def test_ai_spec_holds_forecast_and_allocation_institution_fixed():
    spec = _load_spec()
    assert spec["forecast_state"]["ai_controls_forecast_update"] is False
    assert spec["forecast_state"]["retailer_update"] == "fixed_exponential_smoothing"
    assert spec["forecast_state"]["importer_update"] == "fixed_exponential_smoothing"
    assert spec["actions"]["importer_allocation"]["learned"] is False
    assert spec["actions"]["importer_allocation"]["N_rule"] == "equal_split_no_same_period_reallocation"
    assert spec["actions"]["importer_allocation"]["S_F_rule"] == "equal_split_among_verified_active_exporters"


def test_ai_spec_actions_are_bounded():
    spec = _load_spec()
    assert spec["actions"]["retailer"]["transform"] == "sigmoid_bounded_target_inventory_position"
    assert spec["actions"]["retailer"]["max_target"] == "shelf_life_days_times_own_mean_demand"
    assert spec["actions"]["importer_replenishment"]["transform"] == "sigmoid_bounded_target_inventory_position"
    assert spec["actions"]["importer_replenishment"]["max_target"] == "shelf_life_days_times_aggregate_mean_demand"
    assert spec["actions"]["exporter_readiness"]["transform"] == "sigmoid_bounded_readiness_target"
    assert spec["actions"]["exporter_readiness"]["max_target"] == "current_procurement_requirement"


def test_ai_spec_training_budget_and_evaluation_are_pre_registered():
    spec = _load_spec()
    assert spec["ppo"]["gamma"] == 1.0
    assert spec["ppo"]["hyperparameter_search"] is False
    assert spec["training"]["episodes_per_seed"] == 1000
    assert spec["training"]["episode_horizon_days"] == 1000
    assert spec["training"]["training_seeds"] == [41001, 41002, 41003, 41004, 41005]
    assert spec["training"]["same_network_and_initialization_convention_across_N_S_F"] is True
    assert spec["training"]["early_stopping"] is False
    assert spec["training"]["posthoc_budget_extension_allowed"] is False
    assert spec["training"]["convergence_diagnostic"]["max_absolute_relative_mean_change"] == 0.05
    assert spec["evaluation"]["held_out_replications"] == 200
    assert spec["evaluation"]["evaluation_master_seed"] == 52001
    assert spec["evaluation"]["common_random_numbers_across_six_treatments"] is True
    assert spec["evaluation"]["learning_during_evaluation"] is False
    assert spec["evaluation"]["exploration_during_evaluation"] is False


def test_ai_spec_primary_estimands_outcomes_and_uncertainty_are_locked():
    spec = _load_spec()
    assert spec["factorial_design"]["primary_interactions"] == [
        "vertical_S_minus_N_by_AI",
        "horizontal_F_minus_S_by_AI",
    ]
    assert spec["primary_outcomes"] == [
        "service_level",
        "waste_share_of_terminal_outflow",
        "importer_procurement_bullwhip",
        "mean_total_inventory",
        "mean_abs_target_allocation_gap_exporter_average",
    ]
    assert spec["uncertainty"]["method"] == "hierarchical_bootstrap"
    assert spec["uncertainty"]["bootstrap_resamples"] == 10000
    assert spec["uncertainty"]["independent_training_seed_count"] == 5
    assert spec["uncertainty"]["confirmatory_test_count"] == 10
    assert spec["uncertainty"]["multiplicity_if_significance_claimed"] == "Holm"
