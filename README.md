# eth-dependent-tx-spammer

Transaction spammer for stress testing ModexpWorkchain contracts on Ethereum networks.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Deploy and spam
python3 spammer.py --private-key KEY --rpc RPC_URL

# Spam existing contract (10M gas, 50 gwei)
python3 spammer.py \
  --private-key KEY \
  --rpc RPC_URL \
  --no-deploy \
  --contract ADDRESS \
  --gas-limit 10000000 \
  --gas-price 50 \
  --txs 10
```

## Parameters

- `--rpc` - RPC endpoint (default: Sepolia)
- `--chain-id` - Chain ID (default: 11155111)
- `--private-key` - Private key (required)
- `--gas-limit` - Gas limit per tx (default: 500000)
- `--gas-price` - Gas price in gwei (optional)
- `--rounds` - Modexp rounds per tx (auto-calculated if not set)
- `--txs` - Number of transactions (default: 10)
- `--no-deploy` - Skip deployment
- `--contract` - Contract address (required with --no-deploy)

## Gas Optimization

Rounds are auto-calculated using:
```
rounds = floor((gas_limit * 0.9 - 27000) / 2692)
```

## Tools

- `tools/simulate_gas.py` - Estimate gas without sending transactions

## License

MIT