# Gas Optimization Guide

## Quick Reference

| Gas Limit | Optimal Rounds | Efficiency |
|-----------|---------------|------------|
| 100K      | 23            | 69%        |
| 500K      | 157           | 94%        |
| 1M        | 324           | 97%        |
| 5M        | 1,661         | 99.4%      |
| 10M       | 3,333         | 99.7%      |
| 30M       | 10,020        | 99.9%      |

## Key Metrics
- **Base overhead**: ~27,000 gas (contract call initialization)
- **Cost per round**: ~2,692 gas
- **Formula**: `Max Rounds = (Gas Limit × 0.9 - 27,000) ÷ 2,692`

## Example Commands

### Maximum 10M Gas Transaction
```bash
python3 spammer.py --gas-limit 10000000 --rounds 3333 \
  --private-key YOUR_KEY --rpc YOUR_RPC \
  --no-deploy --contract CONTRACT_ADDRESS
```

### Standard 500K Gas Transaction
```bash
python3 spammer.py --gas-limit 500000 --rounds 157 \
  --private-key YOUR_KEY --rpc YOUR_RPC \
  --no-deploy --contract CONTRACT_ADDRESS
```

## Tools

- `simulate_gas.py` - Uses eth_estimateGas to simulate gas usage without sending transactions
- `spammer.py` - Main tool for deploying contract and sending spam transactions

## Notes
- Apply 10% safety margin to avoid out-of-gas errors
- Higher round counts achieve better efficiency (>99% at 1000+ rounds)
- First transaction typically uses more gas due to storage initialization