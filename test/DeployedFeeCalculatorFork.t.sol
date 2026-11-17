// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

import {FeeDistribution} from "dynamic-fee-pools/src/interfaces/IFeeCalculator.sol";
import {MockPool} from "../src/MockPool.sol";
import {MockTCO2} from "../src/MockTCO2.sol";

interface ICalculatorAtBlock {
    function calculateDepositFees(address pool, address tco2, uint256 amount)
        external view returns (FeeDistribution memory);
    function calculateRedemptionFees(address pool, address[] calldata tco2s, uint256[] calldata amounts)
        external view returns (FeeDistribution memory);
    function getFeeSetup() external view returns (address[] memory, uint256[] memory);
    function depositFeeScale() external view returns (int256);
    function depositFeeRatioScale() external view returns (int256);
    function redemptionFeeScale() external view returns (int256);
    function singleAssetDepositRelativeFee() external view returns (int256);
    function singleAssetRedemptionRelativeFee() external view returns (int256);
}

interface ICharPoolAtBlock {
    function feeCalculator() external view returns (address);
}

/// @notice Fails on actual EVM invariant violations, not on unverified hard-coded
///         historical addresses/parameters. Run only on Base fork at a pinned block.
///         A successful fork call does not prove the published source matches bytecode.
contract DeployedFeeCalculatorForkTest {
    address constant PUBLISHED_CALCULATOR = 0x6A4549759C475d845d4AE074B3656dC257490DA5;
    address constant CHAR_POOL = 0x20b048fA035D5763685D695e66aDF62c5D9F5055;
    address constant TOKEN = address(0xA11CE);

    event HistoricalParameters(
        address calculator,
        address activeModule,
        int256 depositScale,
        int256 ratioScale,
        int256 redemptionScale,
        int256 singleDepositRate,
        int256 singleRedemptionRate
    );
    event HistoricalFeeRecipient(address recipient, uint256 sharePercent);
    event EVMFeeProbe(uint256 secondProjectInventoryWei, bool isDeposit, bool reverted, uint256 feeWei);

    function _total(FeeDistribution memory d) internal pure returns (uint256 z) {
        require(d.recipients.length == d.shares.length, "unequal fee arrays");
        for (uint256 i = 0; i < d.shares.length; ++i) z += d.shares[i];
    }

    function _redemption(
        ICalculatorAtBlock c,
        MockPool p,
        address token,
        uint256 amount
    ) internal view returns (FeeDistribution memory) {
        address[] memory tokens = new address[](1);
        uint256[] memory amounts = new uint256[](1);
        tokens[0] = token;
        amounts[0] = amount;
        return c.calculateRedemptionFees(address(p), tokens, amounts);
    }

    function redemptionProbe(address pool, address token, uint256 amount) external view returns (uint256) {
        return _total(_redemption(ICalculatorAtBlock(PUBLISHED_CALCULATOR), MockPool(pool), token, amount));
    }

    function testDeployedCalculatorIsReadableAndRecipientsSumTo100() public {
        require(PUBLISHED_CALCULATOR.code.length != 0, "no calculator bytecode at fork block");
        ICalculatorAtBlock c = ICalculatorAtBlock(PUBLISHED_CALCULATOR);
        address active = address(0);
        // The published calculator address need not be active for CHAR at the block.
        if (CHAR_POOL.code.length != 0) {
            try ICharPoolAtBlock(CHAR_POOL).feeCalculator() returns (address a) {
                active = a;
            } catch {}
        }
        emit HistoricalParameters(
            PUBLISHED_CALCULATOR,
            active,
            c.depositFeeScale(),
            c.depositFeeRatioScale(),
            c.redemptionFeeScale(),
            c.singleAssetDepositRelativeFee(),
            c.singleAssetRedemptionRelativeFee()
        );
        (address[] memory recipients, uint256[] memory percentages) = c.getFeeSetup();
        require(recipients.length == percentages.length, "fee setup length mismatch");
        require(recipients.length > 0, "fee setup empty at this block");
        uint256 totalShare;
        for (uint256 i = 0; i < recipients.length; ++i) {
            require(recipients[i] != address(0), "zero fee recipient");
            totalShare += percentages[i];
            emit HistoricalFeeRecipient(recipients[i], percentages[i]);
        }
        require(totalShare == 100, "shares do not sum to 100");
    }

    function testDeployedSingleProjectRateAndRounding() public {
        ICalculatorAtBlock c = ICalculatorAtBlock(PUBLISHED_CALCULATOR);
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        p.setInventory(100e18, 100e18);
        uint256 deposit = _total(c.calculateDepositFees(address(p), address(token), 10e18));
        uint256 redemption = _total(_redemption(c, p, address(token), 10e18));
        uint256 depositRate = uint256(c.singleAssetDepositRelativeFee());
        uint256 redemptionRate = uint256(c.singleAssetRedemptionRelativeFee());
        require(depositRate > 0 && redemptionRate > 0, "single-project rate zero");
        require(deposit == 10e18 * depositRate / 1e18, "single-project deposit EVM mismatch");
        require(redemption == 10e18 * redemptionRate / 1e18, "single-project redemption EVM mismatch");
    }

    function testDominantDepositRevertHasCorrectReason() public {
        ICalculatorAtBlock c = ICalculatorAtBlock(PUBLISHED_CALCULATOR);
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        p.setInventory(100e18, 101e18);
        int256 ratio = c.depositFeeRatioScale();
        // Only enforce this expectation for a deployed ratio that actually excludes
        // a 110/111 post-deposit project share, as observed for a ratio of 1.25.
        if (ratio >= 11e17) {
            try c.calculateDepositFees(address(p), address(token), 10e18)
                returns (FeeDistribution memory) {
                revert("expected outside-range revert");
            } catch Error(string memory reason) {
                require(
                    keccak256(bytes(reason)) == keccak256(bytes("Deposit outside range")),
                    "reverted for wrong reason"
                );
            } catch (bytes memory) {
                revert("unexpected custom/panic revert");
            }
        }
    }

    function testNearDominantDepositDomainAndBoundaryGrid() public {
        ICalculatorAtBlock c = ICalculatorAtBlock(PUBLISHED_CALCULATOR);
        MockTCO2 token = new MockTCO2(777);
        MockPool p = new MockPool(address(token));
        uint256[8] memory others = [
            uint256(1e18), uint256(1e17), uint256(1e16), uint256(1e12),
            uint256(1e9), uint256(1e6), uint256(1), uint256(0)
        ];
        for (uint256 i = 0; i < others.length; ++i) {
            p.setInventory(100e18, 100e18 + others[i]);
            try c.calculateDepositFees(address(p), TOKEN, 10e18)
                returns (FeeDistribution memory d) {
                emit EVMFeeProbe(others[i], true, false, _total(d));
            } catch {
                emit EVMFeeProbe(others[i], true, true, 0);
            }
            try this.redemptionProbe(address(p), address(token), 10e18) returns (uint256 fee) {
                emit EVMFeeProbe(others[i], false, false, fee);
            } catch {
                emit EVMFeeProbe(others[i], false, true, 0);
            }
        }
    }
}
