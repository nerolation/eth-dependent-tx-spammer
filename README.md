# Ethereum Transaction Spammer

High-performance blockchain transaction spammer for testing ModexpWorkchain smart contracts on Ethereum networks.

## Features

- **Rapid Fire Mode** - Send transactions without waiting for confirmations
- **Auto-optimization** - Automatically calculates optimal rounds based on gas limit
- **Custom Gas Control** - Specify gas price in gwei
- **Rich CLI** - Professional colorful output with progress tracking
- **Gas Simulation** - Estimate gas usage without sending transactions

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python3 spammer.py --private-key YOUR_KEY --rpc YOUR_RPC_URL
```

### High-throughput Testing (10M gas, custom price)

```bash
python3 spammer.py \
  --private-key YOUR_KEY \
  --rpc YOUR_RPC_URL \
  --no-deploy \
  --contract CONTRACT_ADDRESS \
  --gas-limit 10000000 \
  --gas-price 50 \
  --txs 10
```

### Parameters

- `--rpc` - RPC endpoint URL (default: Sepolia)
- `--chain-id` - Network chain ID (default: 11155111 for Sepolia)
- `--private-key` - Private key for transactions (required)
- `--gas-limit` - Gas limit per transaction (default: 500000)
- `--gas-price` - Gas price in gwei (uses network price if not set)
- `--rounds` - Modexp rounds per TX (auto-calculated if not set)
- `--txs` - Number of transactions to send (default: 10)
- `--no-deploy` - Skip contract deployment
- `--contract` - Contract address (required with --no-deploy)

## Tools

- `spammer.py` - Main transaction spammer
- `simulate_gas.py` - Simulate gas usage with eth_estimateGas
- `gas_profiler.py` - Profile gas consumption patterns

## Gas Optimization

See [GAS_OPTIMIZATION.md](GAS_OPTIMIZATION.md) for optimal gas/rounds ratios.

## License

MIT