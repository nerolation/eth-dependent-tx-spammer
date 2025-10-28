#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from eth_account import Account
from web3 import Web3
from web3.types import TxParams
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box


console = Console()


class BlockchainSpammer:
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        chain_id: int,
        gas_limit: int,
        rounds_per_tx: Optional[int],
        total_txs: int,
        gas_price_gwei: Optional[float] = None,
        contract_name: str = "contract",
        function_args: Optional[list] = None,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            console.print("[bold red]✗ Failed to connect to RPC endpoint[/bold red]")
            raise ConnectionError(f"Failed to connect to RPC endpoint: {rpc_url}")

        self.account = Account.from_key(private_key)
        self.chain_id = chain_id
        self.gas_limit = gas_limit
        self.total_txs = total_txs
        self.contract_name = contract_name
        self.function_args = function_args or []  # Store custom function arguments
        
        # Set gas price (convert from gwei to wei if provided)
        if gas_price_gwei is not None:
            self.gas_price = self.w3.to_wei(gas_price_gwei, 'gwei')
            self.custom_gas_price = True
        else:
            self.gas_price = None  # Will use network's current gas price
            self.custom_gas_price = False
        
        # Calculate optimal rounds if not provided
        if rounds_per_tx is None:
            self.rounds_per_tx = self._calculate_optimal_rounds(gas_limit)
            self.auto_calculated = True
        else:
            self.rounds_per_tx = rounds_per_tx
            self.auto_calculated = False

        # Display connection info
        self._display_connection_info(rpc_url)
    
    def _calculate_optimal_rounds(self, gas_limit: int) -> int:
        """Calculate optimal rounds based on gas limit using the formula:
        Max Rounds = (Gas Limit × 0.9 - 27,000) ÷ 2,692
        """
        BASE_OVERHEAD = 27000
        GAS_PER_ROUND = 2692
        SAFETY_MARGIN = 0.9
        
        optimal_rounds = int((gas_limit * SAFETY_MARGIN - BASE_OVERHEAD) / GAS_PER_ROUND)
        return max(1, optimal_rounds)  # Ensure at least 1 round

    def _display_connection_info(self, rpc_url: str):
        balance = self.w3.eth.get_balance(self.account.address)
        balance_eth = self.w3.from_wei(balance, 'ether')
        
        # Create info table
        info_table = Table(show_header=False, box=box.ROUNDED, padding=1)
        info_table.add_column("Property", style="cyan", width=20)
        info_table.add_column("Value", style="bright_white")
        
        info_table.add_row("🌐 Network", f"[bold]{rpc_url.split('@')[-1] if '@' in rpc_url else rpc_url[:50]}...[/bold]")
        info_table.add_row("🔗 Chain ID", f"[yellow]{self.chain_id}[/yellow]")
        info_table.add_row("📜 Contract Type", f"[cyan]{self.contract_name}[/cyan]")
        info_table.add_row("👤 Account", f"[green]{self.account.address}[/green]")
        info_table.add_row("💰 Balance", f"[bold green]{balance_eth:.6f} ETH[/bold green]")
        info_table.add_row("⚡ Gas Limit", f"[blue]{self.gas_limit:,}[/blue]")
        
        # Display gas price
        if self.custom_gas_price:
            gas_price_gwei = self.w3.from_wei(self.gas_price, 'gwei')
            info_table.add_row("⛽ Gas Price", f"[yellow]{gas_price_gwei:.2f} gwei[/yellow] [dim](custom)[/dim]")
        else:
            current_gas_price = self.w3.eth.gas_price
            gas_price_gwei = self.w3.from_wei(current_gas_price, 'gwei')
            info_table.add_row("⛽ Gas Price", f"[yellow]{gas_price_gwei:.2f} gwei[/yellow] [dim](network)[/dim]")
        
        if self.auto_calculated:
            info_table.add_row("🔄 Rounds/TX", f"[magenta]{self.rounds_per_tx}[/magenta] [dim](auto-optimized)[/dim]")
        else:
            info_table.add_row("🔄 Rounds/TX", f"[magenta]{self.rounds_per_tx}[/magenta]")
        
        # Show function arguments if custom ones are provided
        if self.function_args:
            args_str = ", ".join(str(arg) for arg in self.function_args)
            info_table.add_row("📊 Function Args", f"[cyan]{args_str}[/cyan]")
        
        console.print()
        console.print(Panel(
            info_table,
            title="[bold cyan]🚀 Blockchain Spammer Configuration[/bold cyan]",
            border_style="bright_blue",
            box=box.DOUBLE_EDGE
        ))
        console.print()

    def load_contract_data(self):
        bytecode_path = Path(__file__).parent / "contracts" / f"{self.contract_name}.bytecode"
        abi_path = Path(__file__).parent / "contracts" / f"{self.contract_name}.abi"

        if not bytecode_path.exists():
            raise FileNotFoundError(f"Contract bytecode not found: {bytecode_path}")
        if not abi_path.exists():
            raise FileNotFoundError(f"Contract ABI not found: {abi_path}")

        with open(bytecode_path, "r") as f:
            bytecode = f.read().strip()

        with open(abi_path, "r") as f:
            abi = json.load(f)

        return bytecode, abi

    def deploy_contract(self) -> str:
        console.print(Panel.fit(
            f"[bold yellow]📦 Deploying {self.contract_name} Contract...[/bold yellow]",
            border_style="yellow"
        ))
        
        bytecode, abi = self.load_contract_data()
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)

        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Build transaction
            task = progress.add_task("[cyan]Building deployment transaction...", total=None)
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            transaction: TxParams = {
                "chainId": self.chain_id,
                "gas": self.gas_limit,
                "gasPrice": self.gas_price if self.gas_price else self.w3.eth.gas_price,
                "nonce": nonce,
            }

            constructor = Contract.constructor()
            built_tx = constructor.build_transaction(transaction)
            progress.update(task, description="[green]✓ Transaction built")
            
            # Sign and send
            task2 = progress.add_task("[cyan]Signing and sending transaction...", total=None)
            signed_tx = self.account.sign_transaction(built_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            progress.update(task2, description=f"[green]✓ TX sent: {tx_hash.hex()[:10]}...")
            
            # Wait for confirmation
            task3 = progress.add_task("[cyan]Waiting for confirmation...", total=None)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            progress.update(task3, description="[green]✓ Confirmed!")
            
            # Verify deployment was successful
            task4 = progress.add_task("[cyan]Verifying deployment...", total=None)
            
            # Check receipt status
            if receipt.status != 1:
                progress.update(task4, description="[red]✗ Deployment failed!")
                raise RuntimeError(f"Contract deployment failed. Transaction reverted. TX: {tx_hash.hex()}")
            
            # Check contract address exists
            if not receipt.contractAddress:
                progress.update(task4, description="[red]✗ No contract address!")
                raise RuntimeError(f"No contract address in receipt. TX: {tx_hash.hex()}")
            
            # Check deployed bytecode exists and is not empty
            deployed_bytecode = self.w3.eth.get_code(receipt.contractAddress)
            if not deployed_bytecode or deployed_bytecode == b'' or deployed_bytecode == b'0x':
                progress.update(task4, description="[red]✗ No bytecode at address!")
                raise RuntimeError(f"No bytecode found at contract address {receipt.contractAddress}")
            
            progress.update(task4, description="[green]✓ Deployment verified!")

        contract_address = receipt.contractAddress
        
        # Display deployment result
        result_table = Table(show_header=False, box=box.SIMPLE)
        result_table.add_column("", style="green")
        result_table.add_column("")
        result_table.add_row("✅ Contract deployed:", f"[bold cyan]{contract_address}[/bold cyan]")
        result_table.add_row("⛽ Gas used:", f"[yellow]{receipt.gasUsed:,}[/yellow]")
        result_table.add_row("📝 TX Hash:", f"[dim]{tx_hash.hex()}[/dim]")
        
        console.print()
        console.print(Panel(
            result_table,
            title="[bold green]🎉 Deployment Successful[/bold green]",
            border_style="green"
        ))
        console.print()

        return contract_address

    def spam_transactions(self, contract_address: str):
        _, abi = self.load_contract_data()
        contract = self.w3.eth.contract(address=contract_address, abi=abi)

        # Prepare display message based on contract type and arguments
        if self.function_args:
            if hasattr(contract.functions, 'run'):
                arg1 = self.function_args[0] if len(self.function_args) > 0 else self.rounds_per_tx
                arg2 = self.function_args[1] if len(self.function_args) > 1 else 1
                params_str = f"delta={arg1}, scale={arg2}"
            else:
                arg1 = self.function_args[0] if len(self.function_args) > 0 else self.rounds_per_tx
                params_str = f"rounds={arg1}"
        else:
            params_str = f"{self.rounds_per_tx} rounds"
        
        console.print(Panel.fit(
            f"[bold magenta]🚀 Rapid Fire Mode[/bold magenta]\n"
            f"[cyan]Target:[/cyan] {contract_address}\n"
            f"[cyan]Transactions:[/cyan] {self.total_txs} × {params_str}\n"
            f"[yellow]⚡ Sending without waiting for receipts[/yellow]",
            border_style="magenta"
        ))
        console.print()

        tx_hashes = []
        send_errors = 0
        start_time = time.time()

        with Progress(
            SpinnerColumn(spinner_name="dots12"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task(
                "[cyan]🚀 Rapid firing transactions...", 
                total=self.total_txs
            )
            
            for i in range(self.total_txs):
                try:
                    # Prepare transaction
                    nonce = self.w3.eth.get_transaction_count(self.account.address) + len(tx_hashes)
                    
                    tx: TxParams = {
                        "chainId": self.chain_id,
                        "gas": self.gas_limit,
                        "gasPrice": self.gas_price if self.gas_price else self.w3.eth.gas_price,
                        "nonce": nonce,
                    }

                    # Dynamically call the appropriate function based on available contract functions
                    function_call = None
                    
                    # Check which function is available in the contract
                    if hasattr(contract.functions, 'step'):
                        # Contract has step() function
                        # Use first arg if provided, otherwise use rounds_per_tx
                        arg1 = self.function_args[0] if len(self.function_args) > 0 else self.rounds_per_tx
                        function_call = contract.functions.step(arg1)
                    elif hasattr(contract.functions, 'run'):
                        # Contract has run() function (e.g., contract_brancher)
                        # run(delta, scale) - use custom args or defaults
                        arg1 = self.function_args[0] if len(self.function_args) > 0 else self.rounds_per_tx
                        arg2 = self.function_args[1] if len(self.function_args) > 1 else 1
                        function_call = contract.functions.run(arg1, arg2)
                    else:
                        raise ValueError(f"Contract does not have a supported function (step or run)")
                    
                    built_tx = function_call.build_transaction(tx)
                    signed_tx = self.account.sign_transaction(built_tx)
                    
                    # Send transaction WITHOUT waiting
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    tx_hashes.append(tx_hash)
                    
                    progress.update(
                        main_task, 
                        advance=1,
                        description=f"[cyan]🚀 Sent {i+1}/{self.total_txs} - {tx_hash.hex()[:10]}..."
                    )
                    
                except Exception as e:
                    send_errors += 1
                    progress.console.print(
                        f"  [red]⚠️ TX {i+1}[/red] Send Error: [dim]{str(e)[:50]}[/dim]"
                    )
                    progress.update(main_task, advance=1)

        # Calculate sending rate
        elapsed = time.time() - start_time
        tx_per_second = len(tx_hashes) / elapsed if elapsed > 0 else 0
        
        # Display summary
        console.print()
        self._display_rapid_summary(tx_hashes, send_errors, elapsed, tx_per_second)
        
        # Check receipts for all sent transactions
        if tx_hashes:
            self._check_receipts(tx_hashes)

    def _display_rapid_summary(self, tx_hashes: list, send_errors: int, elapsed: float, tx_per_second: float):
        """Display summary for rapid fire mode"""
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Metric", style="cyan", width=25)
        stats_table.add_column("Value", style="bright_white")
        
        total_sent = len(tx_hashes)
        
        stats_table.add_row("🚀 Transactions Sent", f"[bold green]{total_sent}[/bold green]")
        stats_table.add_row("⚠️  Send Errors", f"[bold red]{send_errors}[/bold red]")
        stats_table.add_row("⏱️  Time Elapsed", f"[yellow]{elapsed:.2f} seconds[/yellow]")
        stats_table.add_row("⚡ Send Rate", f"[bold cyan]{tx_per_second:.1f} TX/second[/bold cyan]")
        stats_table.add_row("💰 Estimated Gas", f"[dim]{total_sent * self.gas_limit:,} (max)[/dim]")
        
        console.print(Panel(
            stats_table,
            title="[bold green]🎯 Rapid Fire Complete![/bold green]",
            border_style="green",
            box=box.DOUBLE
        ))
        
        # Display transaction hashes
        if tx_hashes:
            console.print("\n[bold cyan]📝 Transaction Hashes:[/bold cyan]")
            for i, tx_hash in enumerate(tx_hashes[:5], 1):
                console.print(f"  [dim]{i}.[/dim] {tx_hash.hex()}")
            if len(tx_hashes) > 5:
                console.print(f"  [dim]... and {len(tx_hashes) - 5} more[/dim]")
        
        console.print()
        console.print("[yellow]ℹ️  Checking transaction receipts...[/yellow]")
        console.print()
    
    def _check_receipts(self, tx_hashes: list):
        """Check receipts for all sent transactions"""
        console.print(Panel.fit(
            "[bold yellow]🔍 Checking Transaction Receipts[/bold yellow]",
            border_style="yellow"
        ))
        console.print()
        
        successful = 0
        failed = 0
        pending = 0
        total_gas_used = 0
        
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            check_task = progress.add_task(
                "[cyan]Checking receipts...", 
                total=len(tx_hashes)
            )
            
            for i, tx_hash in enumerate(tx_hashes, 1):
                try:
                    # Try to get receipt with timeout
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                    
                    if receipt.status == 1:
                        successful += 1
                        total_gas_used += receipt.gasUsed
                        progress.console.print(
                            f"  [green]✅ TX {i}[/green] {tx_hash.hex()[:10]}... "
                            f"[dim]Block: {receipt.blockNumber}, Gas: {receipt.gasUsed:,}[/dim]"
                        )
                    else:
                        failed += 1
                        progress.console.print(
                            f"  [red]❌ TX {i}[/red] {tx_hash.hex()[:10]}... [dim]Reverted[/dim]"
                        )
                    
                except Exception as e:
                    # Transaction might be pending or failed to be included
                    pending += 1
                    progress.console.print(
                        f"  [yellow]⏳ TX {i}[/yellow] {tx_hash.hex()[:10]}... [dim]Timeout/Pending[/dim]"
                    )
                
                progress.update(check_task, advance=1)
        
        # Display final receipt summary
        console.print()
        self._display_receipt_summary(successful, failed, pending, total_gas_used, len(tx_hashes))

    def _display_receipt_summary(self, successful: int, failed: int, pending: int, total_gas_used: int, total: int):
        """Display summary of receipt checking"""
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Status", style="cyan", width=25)
        stats_table.add_column("Count", style="bright_white")
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        stats_table.add_row("✅ Confirmed", f"[bold green]{successful}[/bold green]")
        stats_table.add_row("❌ Reverted", f"[bold red]{failed}[/bold red]")
        stats_table.add_row("⏳ Pending/Timeout", f"[bold yellow]{pending}[/bold yellow]")
        stats_table.add_row("📊 Success Rate", f"[bold]{'%.1f' % success_rate}%[/bold]")
        
        if successful > 0:
            avg_gas = total_gas_used // successful
            stats_table.add_row("⛽ Total Gas Used", f"[yellow]{total_gas_used:,}[/yellow]")
            stats_table.add_row("📊 Avg Gas/TX", f"[yellow]{avg_gas:,}[/yellow]")
        
        # Choose title based on success rate
        if success_rate >= 90:
            title = "[bold green]✅ Excellent Results![/bold green]"
            border_color = "green"
        elif success_rate >= 70:
            title = "[bold yellow]⚠️ Mixed Results[/bold yellow]"
            border_color = "yellow"
        else:
            title = "[bold red]❌ Poor Results[/bold red]"
            border_color = "red"
        
        console.print(Panel(
            stats_table,
            title=title,
            border_style=border_color,
            box=box.DOUBLE
        ))
        console.print()

    def _display_summary(self, successful: int, failed: int, total_gas: int, tx_results: list):
        # Create summary statistics
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Metric", style="cyan", width=20)
        stats_table.add_column("Value", style="bright_white")
        
        total = successful + failed
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Color code success rate
        if success_rate >= 90:
            rate_color = "green"
        elif success_rate >= 70:
            rate_color = "yellow"
        else:
            rate_color = "red"
        
        stats_table.add_row("📊 Total Transactions", f"[bold]{total}[/bold]")
        stats_table.add_row("✅ Successful", f"[bold green]{successful}[/bold green]")
        stats_table.add_row("❌ Failed", f"[bold red]{failed}[/bold red]")
        stats_table.add_row("📈 Success Rate", f"[bold {rate_color}]{success_rate:.1f}%[/bold {rate_color}]")
        
        if successful > 0:
            stats_table.add_row("⛽ Total Gas Used", f"[yellow]{total_gas:,}[/yellow]")
            stats_table.add_row("📊 Avg Gas/TX", f"[yellow]{total_gas // successful:,}[/yellow]")
            stats_table.add_row("💎 Gas Efficiency", f"[cyan]{(total_gas / (successful * self.gas_limit) * 100):.1f}%[/cyan]")
        
        # Create final panel
        title = "[bold green]🎊 Spam Complete![/bold green]" if success_rate >= 90 else "[bold yellow]⚠️ Spam Complete with Issues[/bold yellow]"
        
        console.print(Panel(
            stats_table,
            title=title,
            border_style="green" if success_rate >= 90 else "yellow",
            box=box.DOUBLE
        ))
        console.print()

    def run(self, deploy: bool = True, contract_address: Optional[str] = None):
        if deploy:
            contract_address = self.deploy_contract()
        elif not contract_address:
            console.print("[bold red]❌ Must provide contract address if not deploying[/bold red]")
            raise ValueError("Must provide contract address if not deploying")

        self.spam_transactions(contract_address)


def main():
    # Create fancy header
    header = Text("⚡ BLOCKCHAIN TRANSACTION SPAMMER ⚡", style="bold magenta", justify="center")
    subheader = Text("High-Performance Testing Tool for ModexpWorkchain", style="cyan", justify="center")
    
    console.print()
    console.print(Panel(
        header + "\n" + subheader,
        border_style="bright_blue",
        box=box.DOUBLE_EDGE
    ))
    console.print()
    
    parser = argparse.ArgumentParser(
        description="Blockchain transaction spammer for testing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--rpc",
        default="https://eth-sepolia.g.alchemy.com/v2/demo",
        help="RPC endpoint URL",
    )

    parser.add_argument(
        "--chain-id",
        type=int,
        default=11155111,
        help="Chain ID (11155111 for Sepolia)",
    )

    parser.add_argument(
        "--private-key",
        required=True,
        help="Private key for sending transactions",
    )

    parser.add_argument(
        "--gas-limit",
        type=int,
        default=500000,
        help="Gas limit per transaction",
    )

    parser.add_argument(
        "--gas-price",
        type=float,
        default=None,
        help="Gas price in gwei (uses network price if not specified)",
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of modexp rounds per transaction (auto-calculated if not specified)",
    )

    parser.add_argument(
        "--txs",
        type=int,
        default=10,
        help="Total number of transactions to send",
    )

    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Skip contract deployment",
    )

    parser.add_argument(
        "--contract",
        help="Contract address (required if --no-deploy is used)",
    )

    parser.add_argument(
        "--contract-name",
        default="contract",
        help="Name of the contract files to load (without extension, e.g., 'contract' or 'contract_brancher')",
    )

    parser.add_argument(
        "--arg1",
        type=int,
        help="First argument for contract function (e.g., rounds for step() or delta for run())",
    )

    parser.add_argument(
        "--arg2",
        type=int,
        help="Second argument for contract function (e.g., scale for run())",
    )

    parser.add_argument(
        "--args",
        nargs="+",
        type=int,
        help="Multiple arguments for contract function (alternative to --arg1 --arg2)",
    )

    args = parser.parse_args()

    if args.no_deploy and not args.contract:
        console.print("[bold red]❌ Error: --contract is required when using --no-deploy[/bold red]")
        sys.exit(1)

    try:
        # Prepare function arguments
        function_args = []
        if args.args:
            # Use --args if provided
            function_args = args.args
        else:
            # Otherwise use individual --arg1 --arg2 if provided
            if args.arg1 is not None:
                function_args.append(args.arg1)
            if args.arg2 is not None:
                function_args.append(args.arg2)
        
        spammer = BlockchainSpammer(
            rpc_url=args.rpc,
            private_key=args.private_key,
            chain_id=args.chain_id,
            gas_limit=args.gas_limit,
            rounds_per_tx=args.rounds,
            total_txs=args.txs,
            gas_price_gwei=args.gas_price,
            contract_name=args.contract_name,
            function_args=function_args,
        )

        spammer.run(deploy=not args.no_deploy, contract_address=args.contract)
        
        console.print(Panel.fit(
            "[bold green]✨ All operations completed successfully![/bold green]",
            border_style="green"
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]💥 Fatal Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()