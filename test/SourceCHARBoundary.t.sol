// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

import {FeeCalculator} from "dynamic-fee-pools/src/FeeCalculator.sol";
import {FeeDistribution} from "dynamic-fee-pools/src/interfaces/IFeeCalculator.sol";
import {MockPool} from "../src/MockPool.sol";

/// @notice Tests pinned public source; NOT proof of behavior of the live CHAR proxy.
contract SourceCHARBoundaryTest {
    FeeCalculator internal calculator;
    MockPool internal pool;
    address internal constant TOKEN = address(0xA11CE);

    event Probe(uint256 secondProjectWei, bool deposit, bool reverted, uint256 totalFeeWei);

    function setUp() public {
        calculator = new FeeCalculator();
        pool = new MockPool(TOKEN);
        address[] memory recipients = new address[](2);
        recipients[0] = address(0xBEEF);
        recipients[1] = address(0xCAFE);
        uint256[] memory shares = new uint256[](2);
        shares[0] = 60;
        shares[1] = 40;
        calculator.feeSetup(recipients, shares);
    }

    function _total(FeeDistribution memory d) internal pure returns (uint256 x) {
        require(d.recipients.length == d.shares.length, "bad allocation");
        for (uint256 i = 0; i < d.shares.length; ++i) x += d.shares[i];
    }

    function _redeem(uint256 amount) internal view returns (FeeDistribution memory) {
        address[] memory tokens = new address[](1);
        uint256[] memory amounts = new uint256[](1);
        tokens[0] = TOKEN;
        amounts[0] = amount;
        return calculator.calculateRedemptionFees(address(pool), tokens, amounts);
    }

    function testSingleProjectAndFeeSplit() public {
        pool.setInventory(100e18, 100e18);
        FeeDistribution memory d = calculator.calculateDepositFees(address(pool), TOKEN, 10e18);
        require(_total(d) == 1e18, "single-project deposit not 10%");
        require(d.shares.length == 2 && d.shares[0] == 6e17 && d.shares[1] == 4e17, "wrong shares");
        require(_total(_redeem(10e18)) == 1e18, "single-project redeem not 10%");
    }

    function testTwoProjectDepositDiffersFromSingleProject() public {
        pool.setInventory(100e18, 101e18);
        uint256 fee = _total(calculator.calculateDepositFees(address(pool), TOKEN, 10e18));
        require(fee > 1e18, "interior source formula not larger here");
    }

    // Emit raw EVM fixed-point outputs. Catch reverts; do not assume continuity
    // survives precision loss or minimum nonzero fee requirements.
    function testBoundaryGridRevertsAndRounding() public {
        uint256[10] memory others = [
            uint256(1e18), uint256(1e17), uint256(1e16),
            uint256(1e14), uint256(1e12), uint256(1e9),
            uint256(1e6), uint256(1e3), uint256(1), uint256(0)
        ];
        for (uint256 i = 0; i < others.length; ++i) {
            pool.setInventory(100e18, 100e18 + others[i]);
            try calculator.calculateDepositFees(address(pool), TOKEN, 10e18)
                returns (FeeDistribution memory d) {
                emit Probe(others[i], true, false, _total(d));
            } catch {
                emit Probe(others[i], true, true, 0);
            }
            // Calling through external function to make try/catch meaningful.
            try this.redemptionProbe(10e18) returns (uint256 x) {
                emit Probe(others[i], false, false, x);
            } catch {
                emit Probe(others[i], false, true, 0);
            }
        }
    }

    function redemptionProbe(uint256 amount) external view returns (uint256) {
        return _total(_redeem(amount));
    }

    function testFuzzSingleProjectTenPercent(uint64 amount) public {
        // integer units are multiplied by 1e18 to avoid dust-fee-reverts
        if (amount == 0 || amount > 1000) return;
        pool.setInventory(1000e18, 1000e18);
        uint256 fee = _total(calculator.calculateDepositFees(address(pool), TOKEN, uint256(amount) * 1e18));
        require(fee == (uint256(amount) * 1e17), "incorrect flat deposit rate");
    }
}
