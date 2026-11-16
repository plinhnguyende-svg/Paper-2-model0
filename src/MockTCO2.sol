// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

/// @notice Historical Toucan TCO2 getVintageData ABI fixture.
/// Only used to provide a realistic token contract to the deployed FeeCalculator.
/// Not a deployed TCO2 or evidence of project identity.
contract MockTCO2 {
    struct VintageData {
        string name;
        uint64 startTime;
        uint64 endTime;
        uint256 projectTokenId;
        uint64 totalVintageQuantity;
        bool isCorsiaCompliant;
        bool isCCPcompliant;
        string coBenefits;
        string correspAdjustment;
        string additionalCertification;
        string uri;
        string registry;
    }
    uint256 public immutable projectId;
    constructor(uint256 projectId_) { projectId = projectId_; }
    function getVintageData() external view returns (VintageData memory v) {
        v.projectTokenId = projectId;
        v.name = "test-vintage";
        v.registry = "TEST ONLY";
    }
}
