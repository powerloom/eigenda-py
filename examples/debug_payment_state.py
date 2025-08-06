#!/usr/bin/env python3
"""Debug payment state to see what the disperser returns."""

import os
import time
from dotenv import load_dotenv
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.payment import PaymentConfig
from eth_account import Account


def main():
    """Debug payment state."""
    print("EigenDA Payment State Debug")
    print("===========================\n")
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    private_key = os.environ.get("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("❌ Error: EIGENDA_PRIVATE_KEY environment variable not set")
        return
    
    # Create account and signer
    account = Account.from_key(private_key)
    signer = LocalBlobRequestSigner(private_key)
    
    print(f"Account address: {account.address}")
    
    # Create client
    print("\nCreating client...")
    client = DisperserClientV2Full(
        hostname=os.environ.get("EIGENDA_DISPERSER_HOST", "disperser-testnet-sepolia.eigenda.xyz"),
        port=int(os.environ.get("EIGENDA_DISPERSER_PORT", "443")),
        use_secure_grpc=os.environ.get("EIGENDA_USE_SECURE_GRPC", "true").lower() == "true",
        signer=signer,
        payment_config=PaymentConfig()
    )
    
    # Get simple payment state
    print("\n1. Getting simple payment state (GetPaymentState)...")
    try:
        state = client.get_payment_state()
        print("✅ Success!")
        
        # Check all fields
        print("\nPayment State Fields:")
        
        # Reservation
        if hasattr(state, 'reservation'):
            print("\n  reservation field exists")
            if state.HasField('reservation'):
                print("  ✅ Has reservation data")
                res = state.reservation
                print(f"    - start_timestamp: {res.start_timestamp}")
                print(f"    - end_timestamp: {res.end_timestamp}")
                print(f"    - symbols_per_second: {res.symbols_per_second}")
                if hasattr(res, 'quorum_numbers'):
                    print(f"    - quorum_numbers: {list(res.quorum_numbers)}")
                if hasattr(res, 'quorum_splits'):
                    print(f"    - quorum_splits length: {len(res.quorum_splits)}")
            else:
                print("  ❌ No reservation data")
        
        # Cumulative payment
        if hasattr(state, 'cumulative_payment'):
            cp = state.cumulative_payment
            if cp:
                print(f"\n  cumulative_payment: {int.from_bytes(cp, 'big')} wei")
            else:
                print("\n  cumulative_payment: empty (0)")
                
        # On-chain cumulative payment
        if hasattr(state, 'onchain_cumulative_payment'):
            ocp = state.onchain_cumulative_payment
            if ocp:
                print(f"  onchain_cumulative_payment: {int.from_bytes(ocp, 'big')} wei")
            else:
                print("  onchain_cumulative_payment: empty (0)")
        
        # Payment global params
        if hasattr(state, 'payment_global_params'):
            print("\n  payment_global_params field exists")
            if state.HasField('payment_global_params'):
                print("  ✅ Has global params")
                params = state.payment_global_params
                if hasattr(params, 'min_num_symbols'):
                    print(f"    - min_num_symbols: {params.min_num_symbols}")
                if hasattr(params, 'on_demand_quorum_numbers'):
                    print(f"    - on_demand_quorum_numbers: {list(params.on_demand_quorum_numbers)}")
                if hasattr(params, 'price_per_symbol'):
                    print(f"    - price_per_symbol: {params.price_per_symbol}")
                if hasattr(params, 'reservation_window'):
                    print(f"    - reservation_window: {params.reservation_window}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Try advanced payment state
    print("\n\n2. Getting advanced payment state (GetPaymentStateForAllQuorums)...")
    try:
        state = client.get_payment_state_for_all_quorums()
        if state:
            print("✅ Success!")
            
            # Check fields
            if hasattr(state, 'quorum_reservations'):
                print(f"\n  quorum_reservations: {len(state.quorum_reservations)} entries")
            if hasattr(state, 'quorum_configs'):
                print(f"  quorum_configs: {len(state.quorum_configs)} entries")
        else:
            print("❌ Returned None (not implemented)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✨ Debug completed!")


if __name__ == "__main__":
    main()