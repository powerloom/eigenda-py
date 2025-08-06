#!/usr/bin/env python3
"""Example demonstrating reservation-only blob dispersal (no on-demand fallback)."""

import os
import time
from dotenv import load_dotenv
from eigenda.auth.signer import LocalBlobRequestSigner
from eigenda.client_v2_full import DisperserClientV2Full
from eigenda.codec.blob_codec import encode_blob_data
from eigenda.payment import PaymentConfig
from eth_account import Account


def main():
    """Demonstrate advanced reservation features."""
    print("EigenDA Advanced Reservations Example")
    print("=====================================\n")
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    private_key = os.environ.get("EIGENDA_PRIVATE_KEY")
    if not private_key:
        print("❌ Error: EIGENDA_PRIVATE_KEY environment variable not set")
        print("Set it with: export EIGENDA_PRIVATE_KEY='your-private-key'")
        return
    
    # Create account and signer
    account = Account.from_key(private_key)
    signer = LocalBlobRequestSigner(private_key)
    
    print(f"Account address: {account.address}")
    
    # Create client with advanced reservations enabled
    print("\nCreating client with advanced reservation support...")
    client = DisperserClientV2Full(
        hostname=os.environ.get("EIGENDA_DISPERSER_HOST", "disperser-testnet-sepolia.eigenda.xyz"),
        port=int(os.environ.get("EIGENDA_DISPERSER_PORT", "443")),
        use_secure_grpc=os.environ.get("EIGENDA_USE_SECURE_GRPC", "true").lower() == "true",
        signer=signer,
        payment_config=PaymentConfig(
            price_per_symbol=447000000,  # 447 gwei per symbol
            min_num_symbols=4096
        ),
        use_advanced_reservations=True  # Enable per-quorum reservations
    )
    
    # Check payment state
    print("\nChecking for reservations...")
    has_reservation = False
    
    # First try advanced per-quorum reservations (like Go client)
    try:
        payment_state = client.get_payment_state_for_all_quorums()
        if payment_state and hasattr(payment_state, 'quorum_reservations') and payment_state.quorum_reservations:
            print("✅ Advanced per-quorum reservations found!")
            print(f"\nReservations for {len(payment_state.quorum_reservations)} quorums:")
            for quorum_id, reservation in payment_state.quorum_reservations.items():
                print(f"  Quorum {quorum_id}:")
                print(f"    - Symbols per second: {reservation.symbols_per_second}")
                print(f"    - Start: {reservation.start_timestamp}")
                print(f"    - End: {reservation.end_timestamp}")
            has_reservation = True
    except Exception as e:
        print("ℹ️  Advanced per-quorum reservations not available")
    
    # If no advanced reservations, try simple reservation (like Rust client)
    if not has_reservation:
        try:
            print("\nChecking simple reservation...")
            simple_state = client.get_payment_state()
            
            if (hasattr(simple_state, 'reservation') and 
                simple_state.HasField('reservation')):
                reservation = simple_state.reservation
                if (reservation.start_timestamp > 0 and 
                    reservation.end_timestamp > 0):
                    current_time = int(time.time())
                    if reservation.start_timestamp <= current_time <= reservation.end_timestamp:
                        print("✅ Simple reservation found!")
                        print(f"   - Valid from: {reservation.start_timestamp}")
                        print(f"   - Valid until: {reservation.end_timestamp}")
                        print(f"   - Current time: {current_time}")
                        has_reservation = True
                        
                        # Switch client to simple mode for this example
                        client.use_advanced_reservations = False
                        client._check_payment_state()  # Refresh with simple mode
                    else:
                        print("❌ Reservation exists but is not active")
                        print(f"   Current time {current_time} is outside reservation period")
        except Exception as e:
            print(f"❌ Error checking simple reservation: {e}")
    
    if not has_reservation:
        print("\n❌ No active reservations found (neither per-quorum nor simple)")
        print("   This example requires an account with an active reservation.")
        return
    
    # Disperse a blob using reservations
    print("\n\nDispersing test blob with reservations...")
    try:
        # Create test data
        test_data = b"Advanced reservation test: " + os.urandom(100)
        encoded_data = encode_blob_data(test_data)
        
        # Force the client to only use reservations by clearing on-demand info
        if hasattr(client, '_on_demand_quorums'):
            client._on_demand_quorums.clear()
        
        # Disperse using reservation payment
        status, blob_key = client.disperse_blob(
            encoded_data,
            blob_version=0,
            quorum_ids=[0, 1]  # Request multiple quorums
        )
        
        print(f"\n✅ Blob dispersed successfully using reservations!")
        print(f"   Status: {status}")
        print(f"   Blob key: {blob_key.hex()}")
        
        # Show period records from ReservationAccountant
        if hasattr(client.accountant, 'get_period_records'):
            print("\n📊 Period Records (Reservation Usage):")
            for quorum_id in [0, 1]:
                records = client.accountant.get_period_records(quorum_id)
                if records:
                    print(f"   Quorum {quorum_id}: {len(records)} period(s) tracked")
                    for record in records:
                        print(f"     - Period {record.index}: {record.usage} symbols used")
                else:
                    print(f"   Quorum {quorum_id}: No usage recorded")
        
    except Exception as e:
        print(f"\n❌ Error dispersing blob: {e}")
        print("   This example requires active per-quorum reservations.")
        print("   The error indicates no valid reservation is available.")
    
    print("\n✨ Example completed!")


if __name__ == "__main__":
    main()