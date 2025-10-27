#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import json
import sys
from pathlib import Path
from statistics import mean, stdev

from eth_account import Account
from web3 import Web3


def profile_gas(rpc_url: str, private_key: str, contract_address: str, chain_id: int = 11155111):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to RPC endpoint: {rpc_url}")

    account = Account.from_key(private_key)
    
    abi_path = Path(__file__).parent / "contract.abi"
    with open(abi_path, "r") as f:
        abi = json.load(f)
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    print("Gas Profiling for ModexpWorkchain Contract")
    print("=" * 60)
    print(f"Contract: {contract_address}")
    print(f"Account: {account.address}")
    print()
    
    round_counts = [1, 5, 10, 20, 30, 50, 75, 100]
    results = []
    
    print(f"{'Rounds':<10} {'Gas Used':<12} {'Gas/Round':<12} {'Status':<10}")
    print("-" * 60)
    
    for rounds in round_counts:
        try:
            nonce = w3.eth.get_transaction_count(account.address)
            
            # First estimate gas
            try:
                estimated_gas = contract.functions.step(rounds).estimate_gas({
                    'from': account.address
                })
            except Exception as e:
                print(f"{rounds:<10} {'---':<12} {'---':<12} ESTIMATE FAILED")
                continue
            
            # Add 20% buffer to estimate
            gas_limit = int(estimated_gas * 1.2)
            
            tx = {
                "chainId": chain_id,
                "gas": gas_limit,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
            }
            
            function_call = contract.functions.step(rounds)
            built_tx = function_call.build_transaction(tx)
            signed_tx = account.sign_transaction(built_tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=15)
            
            if receipt.status == 1:
                gas_used = receipt.gasUsed
                gas_per_round = gas_used / rounds
                results.append({
                    'rounds': rounds,
                    'gas_used': gas_used,
                    'gas_per_round': gas_per_round,
                    'estimated': estimated_gas
                })
                print(f"{rounds:<10} {gas_used:<12,} {gas_per_round:<12.1f} OK")
            else:
                print(f"{rounds:<10} {'---':<12} {'---':<12} TX FAILED")
                
        except Exception as e:
            print(f"{rounds:<10} {'---':<12} {'---':<12} ERROR: {str(e)[:20]}")
    
    print()
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    
    if len(results) >= 2:
        # Calculate gas per round (excluding first transaction due to storage init)
        gas_per_round_avg = mean([r['gas_per_round'] for r in results[1:]])
        gas_per_round_std = stdev([r['gas_per_round'] for r in results[1:]])
        
        print(f"Average gas per round: {gas_per_round_avg:.1f} (±{gas_per_round_std:.1f})")
        print(f"Base overhead (extrapolated): ~{results[1]['gas_used'] - results[1]['rounds'] * gas_per_round_avg:.0f} gas")
        print()
        
        # Recommendations for common gas limits
        common_limits = [100000, 200000, 300000, 500000, 750000, 1000000]
        
        print("RECOMMENDATIONS")
        print("-" * 60)
        print(f"{'Gas Limit':<15} {'Max Rounds':<15} {'Efficiency':<15}")
        print("-" * 60)
        
        for limit in common_limits:
            # Calculate max rounds with 10% safety margin
            safe_limit = limit * 0.9
            base_overhead = results[1]['gas_used'] - results[1]['rounds'] * gas_per_round_avg
            max_rounds = int((safe_limit - base_overhead) / gas_per_round_avg)
            efficiency = (max_rounds * gas_per_round_avg) / safe_limit * 100
            
            if max_rounds > 0:
                print(f"{limit:<15,} {max_rounds:<15} {efficiency:.1f}%")
        
        print()
        print("OPTIMAL CONFIGURATIONS")
        print("-" * 60)
        print("For maximum throughput per transaction:")
        print(f"  • Gas Limit: 750,000")
        print(f"  • Rounds: {int((750000 * 0.9 - base_overhead) / gas_per_round_avg)}")
        print()
        print("For cost efficiency (smaller transactions):")
        print(f"  • Gas Limit: 200,000")
        print(f"  • Rounds: {int((200000 * 0.9 - base_overhead) / gas_per_round_avg)}")
        print()
        print("For balance (recommended):")
        print(f"  • Gas Limit: 500,000")
        print(f"  • Rounds: {int((500000 * 0.9 - base_overhead) / gas_per_round_avg)}")
        

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Profile gas usage for ModexpWorkchain contract")
    parser.add_argument("--rpc", required=True, help="RPC endpoint URL")
    parser.add_argument("--private-key", required=True, help="Private key for sending transactions")
    parser.add_argument("--contract", required=True, help="Contract address")
    parser.add_argument("--chain-id", type=int, default=11155111, help="Chain ID")
    
    args = parser.parse_args()
    
    try:
        profile_gas(args.rpc, args.private_key, args.contract, args.chain_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)