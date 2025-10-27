// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/// @dev Minimal chained modexp with per-tx entropy via prevrandao() ^ counter.
contract ModexpWorkchain {
    uint256 public counter;

    uint256 constant BASE0     = 0x6d6974655f776f726b5f626173655f313233343536373839;
    uint256 constant EXPONENT0 = 0x0102030405060708090a0b0c0d0e0f10;
    uint256 constant MOD0      = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f;

    function step(uint256 rounds) external {
        assembly {
            let c := sload(counter.slot)

            // modexp calldata: [lenB][lenE][lenM][B][E][M]
            let m := mload(0x40)
            mstore(m, 32)
            mstore(add(m, 32), 32)
            mstore(add(m, 64), 32)
            mstore(add(m, 160), MOD0)

            // cheapest per-tx entropy
            let rnd := xor(prevrandao(), c)
            let base := xor(BASE0, rnd)
            let exponent := add(EXPONENT0, or(and(rnd, 0xffffffffffffffffffffffffffffffff), 1))

            for { let i := 0 } lt(i, rounds) { i := add(i, 1) } {
                mstore(add(m, 96), base)
                mstore(add(m, 128), exponent)
                if iszero(call(gas(), 0x05, 0, m, 192, add(m, 224), 32)) { revert(0, 0) }
                let res := mload(add(m, 224))
                base := addmod(base, res, MOD0)
                exponent := add(exponent, 1)
            }

            sstore(counter.slot, add(c, 1))
        }
    }
}
