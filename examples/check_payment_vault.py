#!/usr/bin/env python3
"""Check PaymentVault contract state for the account."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from eigenda.config import get_network_config

# Minimal ABI for the functions we need
PAYMENT_VAULT_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_account", "type": "address"}],
        "name": "getOnDemandTotalDeposit",
        "outputs": [{"internalType": "uint80", "name": "", "type": "uint80"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_account", "type": "address"}],
        "name": "getReservation",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint64", "name": "symbolsPerSecond", "type": "uint64"},
                    {"internalType": "uint64", "name": "startTimestamp", "type": "uint64"},
                    {"internalType": "uint64", "name": "endTimestamp", "type": "uint64"},
                    {"internalType": "bytes", "name": "quorumNumbers", "type": "bytes"},
                    {"internalType": "bytes", "name": "quorumSplits", "type": "bytes"}
                ],
                "internalType": "struct IPaymentVault.Reservation",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pricePerSymbol",
        "outputs": [{"internalType": "uint64", "name": "", "type": "uint64"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "minNumSymbols",
        "outputs": [{"internalType": "uint64", "name": "", "type": "uint64"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def main():
    print("=== PaymentVault Contract Check ===\n")
    
    # Load environment
    load_dotenv()
    
    # Get network configuration
    network_config = get_network_config()
    
    # Get private key and derive account
    private_key = os.environ.get('EIGENDA_PRIVATE_KEY')
    if not private_key:
        print("Error: EIGENDA_PRIVATE_KEY not set")
        return
        
    account = Account.from_key(private_key)
    print(f"Account: {account.address}")
    print(f"Network: {network_config.network_name}\n")
    
    # Get appropriate RPC URL based on network
    if "sepolia" in network_config.network_name.lower():
        rpc_url = "https://ethereum-sepolia.publicnode.com"
    elif "holesky" in network_config.network_name.lower():
        rpc_url = "https://ethereum-holesky.publicnode.com"
    else:
        rpc_url = "https://ethereum.publicnode.com"  # mainnet
    
    # Connect to RPC
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print(f"Error: Could not connect to {network_config.network_name} RPC")
        return
        
    print(f"Connected to {network_config.network_name}, block number: {w3.eth.block_number}")
    
    # Get payment vault address from config
    payment_vault_address = network_config.payment_vault_address
    if not payment_vault_address:
        print(f"Error: No PaymentVault address configured for {network_config.network_name}")
        print("PaymentVault information not available for this network yet.")
        return
    
    print(f"PaymentVault address: {payment_vault_address}")
    
    # Create contract instance
    contract = w3.eth.contract(address=payment_vault_address, abi=PAYMENT_VAULT_ABI)
    
    try:
        # Check on-demand deposit
        deposit = contract.functions.getOnDemandTotalDeposit(account.address).call()
        print(f"\nOn-demand total deposit: {deposit} wei")
        print(f"                        = {Web3.from_wei(deposit, 'ether')} ETH")
        
        # Check reservation
        print("\nChecking reservation...")
        try:
            reservation = contract.functions.getReservation(account.address).call()
            print(f"Reservation found:")
            print(f"  Symbols per second: {reservation[0]}")
            print(f"  Start timestamp: {reservation[1]}")
            print(f"  End timestamp: {reservation[2]}")
            print(f"  Quorum numbers: {reservation[3].hex()}")
            print(f"  Quorum splits: {reservation[4].hex()}")
        except Exception as e:
            print(f"No active reservation (or error): {e}")
            
        # Get pricing info
        price_per_symbol = contract.functions.pricePerSymbol().call()
        min_symbols = contract.functions.minNumSymbols().call()
        
        print(f"\nPricing information:")
        print(f"  Price per symbol: {price_per_symbol} wei")
        print(f"  Minimum symbols: {min_symbols}")
        
        # Calculate cost for a minimal blob
        min_cost = price_per_symbol * min_symbols
        print(f"\nMinimum cost per blob: {min_cost} wei")
        print(f"                     = {Web3.from_wei(min_cost, 'gwei')} gwei")
        
        # Show how many blobs can be dispersed
        if deposit > 0:
            num_blobs = deposit // min_cost
            print(f"\nWith current deposit, can disperse: {num_blobs} minimal blobs")
            
    except Exception as e:
        print(f"Error querying contract: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()