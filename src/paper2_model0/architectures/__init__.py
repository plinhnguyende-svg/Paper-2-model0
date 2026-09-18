from paper2_model0.enums import Regime
from .no_blockchain import NoBlockchainArchitecture
from .selective_blockchain import SelectiveBlockchainArchitecture
from .full_visibility import FullVisibilityArchitecture


def build_architecture(regime: str | Regime):
    value = regime.value if isinstance(regime, Regime) else str(regime)
    if value == "N":
        return NoBlockchainArchitecture()
    if value == "S":
        return SelectiveBlockchainArchitecture()
    if value == "F":
        return FullVisibilityArchitecture()
    raise ValueError(f"Unknown regime: {regime}")


__all__ = [
    "build_architecture",
    "NoBlockchainArchitecture",
    "SelectiveBlockchainArchitecture",
    "FullVisibilityArchitecture",
]
