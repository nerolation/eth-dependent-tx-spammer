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
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            console.print("[bold red]✗ Failed to connect to RPC endpoint[/bold red]")
            raise ConnectionError(f"Failed to connect to RPC endpoint: {rpc_url}")

        self.account = Account.from_key(private_key)
        self.chain_id = chain_id
        self.gas_limit = gas_limit
        self.total_txs = total_txs
        
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
        
        console.print()
        console.print(Panel(
            info_table,
            title="[bold cyan]🚀 Blockchain Spammer Configuration[/bold cyan]",
            border_style="bright_blue",
            box=box.DOUBLE_EDGE
        ))
        console.print()

    def load_contract_data(self):
        bytecode_path = Path(__file__).parent / "contracts" / "contract.bytecode"
        abi_path = Path(__file__).parent / "contracts" / "contract.abi"

        with open(bytecode_path, "r") as f:
            bytecode = f.read().strip()

        with open(abi_path, "r") as f:
            abi = json.load(f)

        return bytecode, abi

    def deploy_contract(self) -> str:
        console.print(Panel.fit(
            "[bold yellow]📦 Deploying ModexpWorkchain Contract...[/bold yellow]",
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
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            progress.update(task2, description=f"[green]✓ TX sent: {tx_hash.hex()[:10]}...")
            
            # Wait for confirmation
            task3 = progress.add_task("[cyan]Waiting for confirmation...", total=None)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            progress.update(task3, description="[green]✓ Confirmed!")

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

        console.print(Panel.fit(
            f"[bold magenta]🚀 Rapid Fire Mode[/bold magenta]\n"
            f"[cyan]Target:[/cyan] {contract_address}\n"
            f"[cyan]Transactions:[/cyan] {self.total_txs} × {self.rounds_per_tx} rounds\n"
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

                    function_call = contract.functions.step(self.rounds_per_tx)
                    built_tx = function_call.build_transaction(tx)
                    signed_tx = self.account.sign_transaction(built_tx)
                    
                    # Send transaction WITHOUT waiting
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
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
        console.print("[yellow]ℹ️  Transactions sent without waiting for confirmation.[/yellow]")
        console.print("[dim]Check blockchain explorer or use eth_getTransactionReceipt to verify status.[/dim]")
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

    args = parser.parse_args()

    if args.no_deploy and not args.contract:
        console.print("[bold red]❌ Error: --contract is required when using --no-deploy[/bold red]")
        sys.exit(1)

    try:
        spammer = BlockchainSpammer(
            rpc_url=args.rpc,
            private_key=args.private_key,
            chain_id=args.chain_id,
            gas_limit=args.gas_limit,
            rounds_per_tx=args.rounds,
            total_txs=args.txs,
            gas_price_gwei=args.gas_price,
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