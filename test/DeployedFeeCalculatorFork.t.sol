// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

import {FeeDistribution} from "dynamic-fee-pools/src/interfaces/IFeeCalculator.sol";
import {MockPool} from "../src/MockPool.sol";
import {MockTCO2} from "../src/MockTCO2.sol";

interface IDeployedFeeCalculator {
    function calculateDepositFees(address pool, address tco2, uint256 amount)
        external view returns (FeeDistribution memory);
    function calculateRedemptionFees(address pool, address[] calldata tco2s, uint256[] calldata amounts)
        external view returns (FeeDistribution memory);
    function getFeeSetup() external view returns (address[] memory, uint256[] memory);
    function depositFeeScale() external view returns (int256);
    function depositFeeRatioScale() external view returns (int256);
    function redemptionFeeScale() external view returns (int256);
    function singleAssetDepositRelativeFee() external view returns (int256);
}

/// @notice Run ONLY against a Base fork pinned to block 58_258_072.
/// This test calls Base's DEPLOYED calculator, NOT a locally deployed source clone.
/// End-of-block state is examined; producer-wallet identity is NOT established.
contract DeployedFeeCalculatorForkTest {
    address constant CALCULATOR = 0x6A4549759C475d845d4AE074B3656dC257490DA5;
    address constant RECIPIENT_A = 0x7d3E7BbD4e9e4e1507FF4a4b488934abfbAcb801;
    address constant RECIPIENT_B = 0xcA07B1B8A2D6767178F7f7038A3c54aC949d9440;

    function _fee(FeeDistribution memory d) internal pure returns (uint256 z) {
        for (uint256 i=0; i<d.shares.length; ++i) z += d.shares[i];
    }

    function testVerifiedBlockParamsAndRecipients() public view {
        IDeployedFeeCalculator c = IDeployedFeeCalculator(CALCULATOR);
        require(c.depositFeeScale() == 15e16, "depositFeeScale");
        require(c.depositFeeRatioScale() == 125e16, "depositFeeRatioScale");
        require(c.redemptionFeeScale() == 30e16, "redemptionFeeScale");
        require(c.singleAssetDepositRelativeFee() == 10e16, "singleAssetDepositRelativeFee");
        (address[] memory addresses, uint256[] memory shares) = c.getFeeSetup();
        require(addresses.length == 2 && shares.length == 2, "recipient array length");
        require(addresses[0] == RECIPIENT_A && addresses[1] == RECIPIENT_B, "recipient addresses");
        require(shares[0] == 75 && shares[1] == 25, "shares");
    }

    function testSingleProjectFeeAtRealCalculator() public {
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        p.setInventory(100e18, 100e18);
        FeeDistribution memory d = IDeployedFeeCalculator(CALCULATOR).calculateDepositFees(
            address(p), address(token), 10e18
        );
        require(_fee(d) == 1e18, "real-calculator single-project 10% fee");
        require(d.shares[0] == 75e16 && d.shares[1] == 25e16, "real-calculator 75/25");
    }

    function testDominantDepositIsOutsideRangeAtDeployedParams() public {
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        p.setInventory(100e18, 101e18);
        // This is a deployed EVM test of the FeeCalculator call:
        // with a ratio scale of 1.25, a dominant asset can be outside range.
        try IDeployedFeeCalculator(CALCULATOR).calculateDepositFees(address(p), address(token), 10e18)
            returns (FeeDistribution memory)
        {
            revert("dominant deposit unexpectedly accepted");
        } catch {
            // Expected revert on deployed FeeCalculator at pinned block.
        }
    }

    function testMinorityDepositWithinRangeAtDeployedParams() public {
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        p.setInventory(10e18, 100e18);
        FeeDistribution memory d = IDeployedFeeCalculator(CALCULATOR).calculateDepositFees(
            address(p), address(token), 10e18
        );
        require(_fee(d) > 0 && _fee(d) < 10e18, "minority deposit fee invalid");
    }
}
