#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import json
from pathlib import Path

from eth_account import Account
from web3 import Web3


def simulate_gas_usage(rpc_url: str, private_key: str, contract_address: str):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to RPC endpoint: {rpc_url}")

    account = Account.from_key(private_key)
    
    abi_path = Path(__file__).parent / "contract.abi"
    with open(abi_path, "r") as f:
        abi = json.load(f)
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    print("Gas Usage Simulation (using eth_estimateGas)")
    print("=" * 80)
    print(f"Contract: {contract_address}")
    print(f"Account: {account.address}")
    print()
    
    # Test various round counts including very high ones
    round_counts = [1, 10, 50, 100, 200, 500, 1000, 2000, 3000, 4000, 5000]
    
    print(f"{'Rounds':<10} {'Est. Gas':<12} {'Gas/Round':<12} {'Efficiency':<10}")
    print("-" * 80)
    
    results = []
    for rounds in round_counts:
        try:
            # Use estimate_gas to simulate without sending transaction
            estimated_gas = contract.functions.step(rounds).estimate_gas({
                'from': account.address
            })
            
            gas_per_round = estimated_gas / rounds
            # Efficiency improves with more rounds due to fixed overhead
            efficiency = (estimated_gas - 25000) / estimated_gas * 100 if estimated_gas > 25000 else 0
            
            results.append({
                'rounds': rounds,
                'gas': estimated_gas,
                'per_round': gas_per_round,
                'efficiency': efficiency
            })
            
            print(f"{rounds:<10} {estimated_gas:<12,} {gas_per_round:<12.1f} {efficiency:.1f}%")
            
        except Exception as e:
            print(f"{rounds:<10} {'FAILED':<12} {'---':<12} Error: {str(e)[:30]}")
    
    if len(results) > 1:
        print()
        print("=" * 80)
        print("ANALYSIS FOR HIGH GAS LIMITS")
        print("=" * 80)
        
        # Calculate average gas per round (exclude first due to initialization)
        avg_per_round = sum(r['per_round'] for r in results[1:]) / len(results[1:])
        base_overhead = results[0]['gas'] - avg_per_round
        
        print(f"Base overhead: ~{base_overhead:,.0f} gas")
        print(f"Average cost per round: ~{avg_per_round:.1f} gas")
        print()
        
        # Calculate optimal rounds for various gas limits including 10M
        gas_limits = [
            (100_000, "100K"),
            (200_000, "200K"), 
            (500_000, "500K"),
            (1_000_000, "1M"),
            (2_000_000, "2M"),
            (5_000_000, "5M"),
            (10_000_000, "10M"),
            (30_000_000, "30M")
        ]
        
        print("OPTIMAL ROUNDS FOR VARIOUS GAS LIMITS")
        print("-" * 80)
        print(f"{'Gas Limit':<15} {'Max Rounds':<15} {'Work Done':<20} {'Efficiency':<10}")
        print("-" * 80)
        
        for limit, label in gas_limits:
            # Use 90% of limit for safety margin
            safe_limit = limit * 0.9
            max_rounds = int((safe_limit - base_overhead) / avg_per_round)
            
            if max_rounds > 0:
                work_done = max_rounds * avg_per_round
                efficiency = (work_done / safe_limit) * 100
                print(f"{label:<15} {max_rounds:<15,} {work_done:>20,.0f} {efficiency:>9.1f}%")
        
        print()
        print("RECOMMENDED CONFIGURATIONS")
        print("-" * 80)
        
        # Calculate for 10M gas specifically
        ten_mil_rounds = int((10_000_000 * 0.9 - base_overhead) / avg_per_round)
        
        print(f"For 10 Million Gas Limit:")
        print(f"  • Rounds: {ten_mil_rounds:,}")
        print(f"  • Estimated actual gas: ~{int(base_overhead + ten_mil_rounds * avg_per_round):,}")
        print(f"  • Safety margin: ~{10_000_000 - int(base_overhead + ten_mil_rounds * avg_per_round):,} gas")
        print()
        print("Command:")
        print(f"python3 spammer.py --gas-limit 10000000 --rounds {ten_mil_rounds} \\")
        print(f"  --private-key YOUR_KEY --rpc YOUR_RPC --contract {contract_address}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulate gas usage with eth_call")
    parser.add_argument("--rpc", required=True, help="RPC endpoint URL")
    parser.add_argument("--private-key", required=True, help="Private key")
    parser.add_argument("--contract", required=True, help="Contract address")
    
    args = parser.parse_args()
    
    simulate_gas_usage(args.rpc, args.private_key, args.contract)