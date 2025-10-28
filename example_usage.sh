#!/bin/bash

# Example usage of the spammer with different contracts and custom arguments

echo "Example 1: Using the default 'contract' contract"
echo "python3 spammer.py --private-key YOUR_KEY --txs 5"
echo ""

echo "Example 2: Using the 'contract_brancher' contract with default arguments"
echo "python3 spammer.py --private-key YOUR_KEY --contract-name contract_brancher --txs 5"
echo ""

echo "Example 3: Contract_brancher with custom delta and scale using --arg1 and --arg2"
echo "python3 spammer.py --private-key YOUR_KEY --contract-name contract_brancher --arg1 100 --arg2 5 --txs 10"
echo ""

echo "Example 4: Contract_brancher with custom arguments using --args (alternative syntax)"
echo "python3 spammer.py --private-key YOUR_KEY --contract-name contract_brancher --args 50 10 --txs 10"
echo ""

echo "Example 5: Default contract with custom rounds argument"
echo "python3 spammer.py --private-key YOUR_KEY --arg1 200 --txs 5"
echo ""

echo "Example 6: Use existing deployed contract_brancher with custom args"
echo "python3 spammer.py --private-key YOUR_KEY --contract-name contract_brancher --no-deploy --contract 0xYOUR_CONTRACT_ADDRESS --arg1 75 --arg2 3 --txs 10"
echo ""

echo "Notes:"
echo "  --arg1: First argument (rounds for step() or delta for run())"
echo "  --arg2: Second argument (scale for run())"
echo "  --args: Alternative way to specify multiple arguments at once"