// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

/// @notice Test-only state adapter for Toucan's published IPool ABI.
contract MockPool {
    uint256 public total;
    uint256 public ownSupply;
    address public immutable selected;

    constructor(address token) { selected = token; }

    function setInventory(uint256 own_, uint256 total_) external {
        require(total_ >= own_, "invalid supply");
        ownSupply = own_;
        total = total_;
    }

    function totalTCO2Supply() external view returns (uint256) {
        return total;
    }

    function totalPerProjectSupply(address token) external view returns (uint256) {
        return token == selected ? ownSupply : 0;
    }

    function totalPerProjectSupply(address token, uint256) external view returns (uint256) {
        return token == selected ? ownSupply : 0;
    }
}
