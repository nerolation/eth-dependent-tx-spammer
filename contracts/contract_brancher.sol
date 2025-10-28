// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice PrefetchHammerFinal — minimal, lab-only changes + proper delta usage
contract PrefetchHammerFinal {
    uint256 private ctr;                    // slot 0 (only mutable)

    uint256 private immutable SALT;
    uint256 private immutable N;            // base synthesized keys per call (default 64)
    uint256 private immutable FAN;          // fan-out per key (default 4)
    uint16   private constant MAX_SCALE = 40;

    constructor() {
        SALT = uint256(keccak256(abi.encodePacked(block.prevrandao, msg.sender, address(this))));
        N = 64;
        FAN = 4;
    }

    /// @param delta tiny per-call entropy
    /// @param scale multiplies the number of synthesized keys (N * scale)
    function run(uint256 delta, uint16 scale) external returns (uint256) {
        require(scale > 0 && scale <= MAX_SCALE, "scale out of range");

        uint256 S = SALT;
        uint256 N_ = N * (scale == 0 ? 1 : scale); // avoid zero (guarded above)
        uint256 FAN_ = FAN;

        assembly {
            let ptr := mload(0x40)

            // increment counter BEFORE mixing
            let cOld := sload(0x0)
            let cNew := add(cOld, 1)
            sstore(0x0, cNew)

            // use the Solidity param directly
            let d := delta
            let shift := add(xor(cNew, d), 1)

            // main loop over N_ synthesized keys
            let i := 0
            for { } lt(i, N_) { i := add(i, 1) } {
                // gas safety: break if remaining gas is low
                if lt(gas(), 100000) { break }

                // base = keccak(shift || i || S || d)
                mstore(ptr, shift)
                mstore(add(ptr,0x20), i)
                mstore(add(ptr,0x40), S)
                mstore(add(ptr,0x60), d)
                let base := keccak256(ptr, 0x80)

                // d0 = keccak(base || 1 || shift || d)
                mstore(ptr, base)
                mstore(add(ptr,0x20), 1)
                mstore(add(ptr,0x40), shift)
                mstore(add(ptr,0x60), d)
                let d0 := keccak256(ptr, 0x80)

                // runtime-dependent branch
                let sv := sload(d0)
                mstore(ptr, xor(sv, caller()))
                mstore(add(ptr,0x20), add(number(), shift))
                let bid := and(keccak256(ptr, 0x40), 3)

                switch bid
                case 0 {
                    let j := 0
                    for { } lt(j, FAN_) { j := add(j, 1) } {
                        mstore(ptr, d0)
                        mstore(add(ptr,0x20), j)
                        mstore(add(ptr,0x40), shift)
                        mstore(add(ptr,0x60), d)
                        let t := keccak256(ptr, 0x80)
                        let tmp := sload(t)
                    }
                }
                case 1 {
                    let j := 0
                    for { } lt(j, FAN_) { j := add(j, 1) } {
                        mstore(ptr, base)
                        mstore(add(ptr,0x20), xor(j, shift))
                        mstore(add(ptr,0x40), S)
                        mstore(add(ptr,0x60), d)
                        let t := keccak256(ptr, 0x80)
                        let tmp := sload(t)
                    }
                }
                case 2 {
                    mstore(ptr, sv)
                    mstore(add(ptr,0x20), base)
                    mstore(add(ptr,0x40), d)
                    let mid := keccak256(ptr, 0x60)
                    let j := 0
                    for { } lt(j, FAN_) { j := add(j, 1) } {
                        mstore(ptr, mid)
                        mstore(add(ptr,0x20), add(j, shift))
                        mstore(add(ptr,0x40), d)
                        let t := keccak256(ptr, 0x60)
                        let tmp := sload(t)
                    }
                }
                default {
                    mstore(ptr, xor(base, caller()))
                    mstore(add(ptr,0x20), xor(shift, number()))
                    mstore(add(ptr,0x40), d)
                    let seed := keccak256(ptr, 0x60)
                    let j := 0
                    for { } lt(j, FAN_) { j := add(j, 1) } {
                        mstore(ptr, seed)
                        mstore(add(ptr,0x20), mul(j, 0x10001))
                        mstore(add(ptr,0x40), sv)
                        mstore(add(ptr,0x60), d)
                        let t := keccak256(ptr, 0x80)
                        let tmp := sload(t)
                    }
                }
            }

            // restore free memory pointer conservatively
            mstore(0x40, add(ptr, 0x80))
        }

        return ctr;
    }
}
