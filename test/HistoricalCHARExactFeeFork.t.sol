// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

/// Gate 25 — independent on-chain calculator quoting at transaction-index-aware state.
/// This checks deployed EVM quotation against independently archived Gate 24 receipt
/// values. It does not establish source-bytecode identity or producer financing.
interface VmGate25 {
    function envString(string calldata key) external returns (string memory);
    function createSelectFork(string calldata urlOrAlias, bytes32 txHash) external returns (uint256 forkId);
    function load(address target, bytes32 slot) external view returns (bytes32);
}

struct FeeDistributionGate25 {
    address[] recipients;
    uint256[] shares;
}

interface IPoolGate25 {
    function feeCalculator() external view returns (address);
    function totalTCO2Supply() external view returns (uint256);
    function totalPerProjectSupply(address project) external view returns (uint256);
}

interface ICalculatorGate25 {
    function calculateDepositFees(address pool, address token, uint256 amount)
        external view returns (FeeDistributionGate25 memory);
    function calculateRedemptionFees(address pool, address[] calldata tokens, uint256[] calldata amounts)
        external view returns (FeeDistributionGate25 memory);
    function getFeeSetup() external view returns (address[] memory, uint256[] memory);
    function depositFeeScale() external view returns (int256);
    function depositFeeRatioScale() external view returns (int256);
    function redemptionFeeScale() external view returns (int256);
    function redemptionFeeShift() external view returns (int256);
}

/// @notice No eth_call at B-1 or at end of B is used as the target prestate.
/// Foundry's fork-by-transaction must reconstruct the preceding transactions
/// within B before these assertions are accepted as an exact quotation.
contract HistoricalCHARExactFeeForkTest {
    VmGate25 private constant vm =
        VmGate25(address(uint160(uint256(keccak256("hevm cheat code")))));
    address private constant POOL = 0x20b048fA035D5763685D695e66aDF62c5D9F5055;
    bytes32 private constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    // Independently observed in the Gate 24 canonical receipt archive, not computed
    // by the calculator currently being tested.
    bytes32 private constant DEPOSIT_TX =
        0x0237beb377836c8ca1bec693cc5d37eff65d3a48b53b68d667fed67839b8193c;
    bytes32 private constant REDEMPTION_TX =
        0xc676a373fc6cec24dd9f744f04a7dd7f975921370be6270185006b25fbd4f034;
    address private constant DEPOSIT_TOKEN =
        0x99f5f445ff1f537686f2fbc32d43653c7c786645;
    address private constant REDEMPTION_TOKEN =
        0xf20cb470acda661ab02de3b7be43894e2ade0b1c;
    address private constant FEE_RECIPIENT_0 =
        0x7d3e7bbd4e9e4e1507ff4a4b488934abfbacb801;
    address private constant FEE_RECIPIENT_1 =
        0xca07b1b8a2d6767178f7f7038a3c54ac949d9440;

    event HistoricalPrestate(
        bytes32 indexed transactionHash,
        uint256 blockNumber,
        uint256 totalInventoryRaw,
        uint256 projectInventoryRaw,
        address activeImplementation,
        bytes32 implementationCodeHash,
        address activeCalculator,
        bytes32 calculatorCodeHash
    );
    event HistoricalParameters(
        bytes32 indexed transactionHash,
        int256 depositScale,
        int256 depositRatioScale,
        int256 redemptionScale,
        int256 redemptionShift
    );
    event HistoricalFeeMatch(
        bytes32 indexed transactionHash,
        bool isDeposit,
        uint256 amountRaw,
        uint256 feeRaw,
        address feeRecipient0,
        uint256 share0,
        address feeRecipient1,
        uint256 share1
    );

    function _selectExactPrestate(bytes32 transactionHash) internal {
        // Aborts on unsupported historical fork or missing configured RPC: fail-closed.
        string memory rpc = vm.envString("BASE_RPC_URL");
        require(bytes(rpc).length > 0, "MISSING_BASE_RPC_URL");
        vm.createSelectFork(rpc, transactionHash);
    }

    function _calculatorAtPrestate(bytes32 txHash, address token)
        internal returns (ICalculatorGate25 calc)
    {
        require(POOL.code.length > 0, "NO_POOL_CODE_AT_TRANSACTION");
        bytes32 rawImplementation = vm.load(POOL, IMPLEMENTATION_SLOT);
        address implementation = address(uint160(uint256(rawImplementation)));
        require(implementation != address(0) && implementation.code.length > 0,
                "MISSING_ACTIVE_POOL_IMPLEMENTATION");
        IPoolGate25 pool = IPoolGate25(POOL);
        address module = pool.feeCalculator();
        require(module != address(0) && module.code.length > 0,
                "MISSING_ACTIVE_FEE_CALCULATOR");
        uint256 total = pool.totalTCO2Supply();
        uint256 current = pool.totalPerProjectSupply(token);
        require(current <= total, "INVALID_PRESTATE_INVENTORY");
        emit HistoricalPrestate(txHash, block.number, total, current, implementation,
                                implementation.codehash, module, module.codehash);
        calc = ICalculatorGate25(module);
        emit HistoricalParameters(txHash, calc.depositFeeScale(),
                                  calc.depositFeeRatioScale(),
                                  calc.redemptionFeeScale(), calc.redemptionFeeShift());
    }

    function _assertReceiptAndIntegerRounding(
        ICalculatorGate25 calc,
        bytes32 txHash,
        bool isDeposit,
        uint256 amount,
        uint256 observedTotalFee,
        uint256 observed0,
        uint256 observed1,
        FeeDistributionGate25 memory predicted
    ) internal {
        (address[] memory recipients, uint256[] memory weights) = calc.getFeeSetup();
        require(recipients.length == 2 && weights.length == 2,
                "FEE_RECIPIENT_NUMBER_DIFFERS_FROM_ARCHIVED_RECEIPT");
        require(predicted.recipients.length == 2 && predicted.shares.length == 2,
                "PREDICTED_FEE_LENGTH_DIFFERENT");
        require(recipients[0] == FEE_RECIPIENT_0 && recipients[1] == FEE_RECIPIENT_1,
                "ACTIVE_RECIPIENTS_DIFFER_FROM_RECEIPT");
        require(predicted.recipients[0] == recipients[0] &&
                predicted.recipients[1] == recipients[1], "QUOTED_RECIPIENT_MISMATCH");
        require(weights[0] + weights[1] == 100, "FEE_WEIGHTS_DO_NOT_SUM_TO_100");
        uint256 quotedTotal = predicted.shares[0] + predicted.shares[1];
        require(quotedTotal == observedTotalFee, "EXACT_CALCULATED_TOTAL_FEE_MISMATCH");
        require(predicted.shares[0] == observed0 &&
                predicted.shares[1] == observed1,
                "EXACT_FEE_RECIPIENT_AMOUNTS_MISMATCH");

        // Published source 7aef954 assigns all division remainder to index 0.
        // Check the arithmetic separately from the deployed fee quote.
        uint256 initial0 = (observedTotalFee * weights[0]) / 100;
        uint256 initial1 = (observedTotalFee * weights[1]) / 100;
        uint256 remainder = observedTotalFee - initial0 - initial1;
        require(observed0 == initial0 + remainder && observed1 == initial1,
                "ARCHIVED_RECEIPT_NOT_CONSISTENT_WITH_SOURCE_INTEGER_ROUNDING");
        emit HistoricalFeeMatch(txHash, isDeposit, amount, quotedTotal,
                                recipients[0], predicted.shares[0],
                                recipients[1], predicted.shares[1]);
    }

    function testHistoricalDepositExactPrestateAndFee() public {
        _selectExactPrestate(DEPOSIT_TX);
        ICalculatorGate25 calc = _calculatorAtPrestate(DEPOSIT_TX, DEPOSIT_TOKEN);
        uint256 amount = 18000000000000000000;
        FeeDistributionGate25 memory d = calc.calculateDepositFees(POOL, DEPOSIT_TOKEN, amount);
        _assertReceiptAndIntegerRounding(calc, DEPOSIT_TX, true, amount,
            299055716169059513, 224291787126794635, 74763929042264878, d);
    }

    function testHistoricalRedemptionExactPrestateAndFee() public {
        _selectExactPrestate(REDEMPTION_TX);
        ICalculatorGate25 calc = _calculatorAtPrestate(REDEMPTION_TX, REDEMPTION_TOKEN);
        uint256 amount = 5000000000000000;
        address[] memory tokens = new address[](1);
        uint256[] memory amounts = new uint256[](1);
        tokens[0] = REDEMPTION_TOKEN;
        amounts[0] = amount;
        FeeDistributionGate25 memory d = calc.calculateRedemptionFees(POOL, tokens, amounts);
        _assertReceiptAndIntegerRounding(calc, REDEMPTION_TX, false, amount,
            9412065557460, 7059049168095, 2353016389365, d);
    }
}
