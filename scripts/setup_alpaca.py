#!/usr/bin/env python3
"""
Alpaca Setup Helper

Interactive script to help configure Alpaca API keys.
"""

import sys
import os
from pathlib import Path


def setup_alpaca_keys():
    """Guide user through Alpaca API key setup"""
    
    print("╔══════════════════════════════════════════════════════╗")
    print("║       ALPACA API KEY SETUP HELPER                    ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    # Check if .env exists
    env_file = Path(__file__).parent.parent / '.env'
    env_example = Path(__file__).parent.parent / '.env.example'
    
    if not env_file.exists():
        print("\n⚠️  No .env file found!")
        print("   Creating from .env.example...")
        
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("   ✅ Created .env file")
        else:
            print("   ❌ .env.example not found!")
            return False
    
    print("\n" + "=" * 58)
    print("📋 STEP 1: Get Alpaca API Keys")
    print("=" * 58)
    print("\n1. Go to: https://alpaca.markets/")
    print("2. Sign up for a FREE paper trading account")
    print("3. After signup, navigate to:")
    print("   Dashboard → Paper Trading → API Keys")
    print("4. Click 'Generate New Key'")
    print("5. Copy BOTH keys (shown only once!)")
    
    print("\n" + "=" * 58)
    print("📋 STEP 2: Enter Your Keys")
    print("=" * 58)
    
    print("\n⚠️  IMPORTANT:")
    print("   - Use PAPER TRADING keys (not live trading)")
    print("   - API Key starts with 'PK...'")
    print("   - Secret Key is a long alphanumeric string")
    print("   - Never share these keys publicly!")
    
    print("\n")
    api_key = input("Enter your Alpaca API Key (PK...): ").strip()
    secret_key = input("Enter your Alpaca Secret Key: ").strip()
    
    # Validate format - API key should start with PK
    if not api_key.startswith('PK'):
        print("\n❌ API Key should start with 'PK'")
        print("   Make sure you're using PAPER TRADING keys")
        return False
    
    # Secret key validation - just check it's not empty and has reasonable length
    if not secret_key or len(secret_key) < 20:
        print("\n❌ Secret Key appears invalid (too short)")
        print("   Make sure you copied the entire secret key")
        return False
    
    print("\n" + "=" * 58)
    print("📋 STEP 3: Update .env File")
    print("=" * 58)
    
    # Read .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update keys
    new_lines = []
    for line in lines:
        if line.startswith('ALPACA_API_KEY='):
            new_lines.append(f'ALPACA_API_KEY={api_key}\n')
        elif line.startswith('ALPACA_SECRET_KEY='):
            new_lines.append(f'ALPACA_SECRET_KEY={secret_key}\n')
        else:
            new_lines.append(line)
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ Updated {env_file}")
    
    print("\n" + "=" * 58)
    print("📋 STEP 4: Test Connection")
    print("=" * 58)
    
    print("\nRunning connection test...")
    
    # Try to import and test
    try:
        # Force reload of settings
        if 'config.settings' in sys.modules:
            del sys.modules['config.settings']
        if 'config' in sys.modules:
            del sys.modules['config']
        
        from wawatrader.alpaca_client import AlpacaClient
        
        print("Connecting to Alpaca...")
        client = AlpacaClient()
        account = client.get_account()
        
        print("\n" + "🎉" * 29)
        print("✅ CONNECTION SUCCESSFUL!")
        print("🎉" * 29)
        
        print(f"\n📊 Your Paper Trading Account:")
        print(f"   Account Number: {account['account_number']}")
        print(f"   Status: {account['status']}")
        print(f"   Buying Power: ${account['buying_power']:,.2f}")
        print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
        
        print("\n" + "=" * 58)
        print("🚀 READY TO GO!")
        print("=" * 58)
        print("\nYou can now:")
        print("  • Run full test: python tests/test_alpaca.py")
        print("  • View account: python wawatrader/alpaca_client.py")
        print("  • Continue to Task 3: Technical Indicators")
        print("=" * 58)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 58)
        print("❌ CONNECTION FAILED")
        print("=" * 58)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Double-check your API keys are correct")
        print("2. Make sure you copied PAPER TRADING keys")
        print("3. Verify keys start with PK... and SK...")
        print("4. Try regenerating keys in Alpaca dashboard")
        print("5. Check internet connection")
        print("\nFor help, see SETUP.md")
        return False


if __name__ == "__main__":
    try:
        success = setup_alpaca_keys()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
