#!/usr/bin/env python3
"""
WawaTrader Starter Script

Quick launcher for all main WawaTrader components.
By default, starts the complete system (trading + dashboard).

Usage:
    python start.py                    # Start full system: trading + dashboard (default)
    python start.py menu               # Show all available commands
    python start.py dashboard          # Start dashboard only
    python start.py trading            # Start trading agent only
    python start.py backtest          # Run backtest
    python start.py config            # Open config UI
    python start.py status            # Check system status
    python start.py test              # Run tests
    python start.py demo [component]  # Run demos
    python start.py help              # Detailed help
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional
import os

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Virtual environment paths to check
VENV_PATHS = [
    PROJECT_ROOT / 'venv',
    PROJECT_ROOT / '.venv',
    Path.home() / '.pyenv' / 'versions' / 'wawatrader',
    Path('/opt/homebrew/var/pyenv/versions/wawatrader')
]

# Available commands and their descriptions
COMMANDS = {
    'full': {
        'script': 'scripts/run_trading.py',
        'description': 'Start complete system (trading + dashboard)',
        'help': 'Runs trading agent with integrated dashboard'
    },
    'dashboard': {
        'script': 'scripts/run_dashboard.py',
        'description': 'Start the real-time trading dashboard only (Plotly/Dash)',
        'help': 'Opens web interface at http://localhost:8050'
    },
    'trading': {
        'script': 'scripts/run_trading.py', 
        'description': 'Start the main trading agent only',
        'help': 'Begins paper trading with LLM + technical analysis'
    },
    'backtest': {
        'script': 'scripts/run_backtest.py',
        'description': 'Run historical backtesting',
        'help': 'Test strategies on historical data'
    },
    'config': {
        'script': 'scripts/run_config_ui.py',
        'description': 'Open configuration web interface',
        'help': 'Configure settings via web UI at http://localhost:8051'
    },
    'status': {
        'script': 'scripts/status_check.py',
        'description': 'Check system status and health',
        'help': 'Verify all components are working properly'
    },
    'test': {
        'description': 'Run the test suite',
        'help': 'Execute all unit and integration tests'
    }
}

# Demo components
DEMOS = {
    'dashboard': 'scripts/demo_dashboard.py',
    'alerts': 'scripts/demo_alerts.py', 
    'backtest': 'scripts/demo_backtest.py',
    'database': 'scripts/demo_database.py',
    'config': 'scripts/demo_config_ui.py'
}

def print_header():
    """Print WawaTrader header"""
    print("🚀 " + "="*60)
    print("   WawaTrader - Hybrid LLM Algorithmic Trading System")
    print("   Paper Trading • Risk Management • Real-time Dashboard")
    print("="*64)
    print()

def print_menu():
    """Print available commands menu"""
    print("📋 Available Commands:")
    print("-" * 40)
    
    # Show full command first as it's the default
    print(f"  {'full':<12} - {COMMANDS['full']['description']} (default)")
    
    # Show other commands
    for cmd, info in COMMANDS.items():
        if cmd != 'full':  # Skip full since we already showed it
            print(f"  {cmd:<12} - {info['description']}")
    
    print(f"  {'demo':<12} - Run component demos")
    print(f"  {'menu':<12} - Show this menu")
    print(f"  {'help':<12} - Show detailed help")
    print()
    
    print("💡 Usage Examples:")
    print("   python start.py              # Start full system (default)")
    print("   python start.py dashboard    # Dashboard only")
    print("   python start.py trading      # Trading agent only")
    print("   python start.py menu         # Show all options")
    print("   python start.py demo alerts  # Run alerts demo")
    print()

def print_help():
    """Print detailed help for all commands"""
    print("📖 Detailed Command Help:")
    print("-" * 50)
    
    for cmd, info in COMMANDS.items():
        print(f"\n🔧 {cmd.upper()}")
        print(f"   Description: {info['description']}")
        print(f"   Help: {info['help']}")
        if 'script' in info:
            print(f"   Script: {info['script']}")
    
    print(f"\n🎮 DEMO")
    print(f"   Description: Run interactive component demonstrations")
    print(f"   Available demos: {', '.join(DEMOS.keys())}")
    print(f"   Usage: python start.py demo [component]")
    print()

def run_command(cmd: str, args: Optional[list] = None) -> bool:
    """Run a command with optional arguments"""
    args = args or []
    
    try:
        if cmd == 'test':
            # Special case for running tests
            python_exe = find_venv_python() or 'python'
            print("🧪 Running WawaTrader test suite...")
            print(f"   Using Python: {python_exe}")
            result = subprocess.run([python_exe, '-m', 'pytest', 'tests/', '-v'], 
                                  cwd=PROJECT_ROOT, check=False)
            return result.returncode == 0
            
        elif cmd == 'demo':
            if not args or args[0] not in DEMOS:
                print(f"❌ Available demos: {', '.join(DEMOS.keys())}")
                return False
            
            demo_script = DEMOS[args[0]]
            python_exe = find_venv_python() or 'python'
            print(f"🎮 Running {args[0]} demo...")
            result = subprocess.run([python_exe, demo_script], 
                                  cwd=PROJECT_ROOT, check=False)
            return result.returncode == 0
            
        elif cmd in COMMANDS and 'script' in COMMANDS[cmd]:
            script = COMMANDS[cmd]['script']
            python_exe = find_venv_python() or 'python'
            print(f"▶️  Starting {cmd}...")
            print(f"   Script: {script}")
            print(f"   Python: {python_exe}")
            print(f"   Help: {COMMANDS[cmd]['help']}")
            print()
            
            # Run the script with proper Python environment
            result = subprocess.run([python_exe, script] + args, 
                                  cwd=PROJECT_ROOT, check=False)
            return result.returncode == 0
            
        else:
            print(f"❌ Unknown command: {cmd}")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped {cmd}")
        return True
    except FileNotFoundError as e:
        print(f"❌ Script not found: {e}")
        print(f"   Make sure you're in the WawaTrader root directory")
        return False
    except Exception as e:
        print(f"❌ Error running {cmd}: {e}")
        return False

def find_venv_python() -> Optional[str]:
    """Find the Python executable in virtual environment"""
    # Check if we're already in a venv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Already in virtual environment")
        return sys.executable
    
    # Look for venv in common locations
    for venv_path in VENV_PATHS:
        if sys.platform == "win32":
            python_exe = venv_path / 'Scripts' / 'python.exe'
        else:
            python_exe = venv_path / 'bin' / 'python'
        
        if python_exe.exists():
            print(f"✅ Found virtual environment: {venv_path}")
            return str(python_exe)
    
    # If no venv found, warn but continue with system Python
    print("⚠️  No virtual environment found - using system Python")
    print("   Consider running: python -m venv venv && source venv/bin/activate")
    return sys.executable

def check_environment() -> bool:
    """Check if we're in the right environment"""
    # Check if we're in the right directory
    if not (PROJECT_ROOT / 'wawatrader').exists():
        print("❌ Error: Not in WawaTrader root directory")
        print("   Please run this script from the WawaTrader project root")
        return False
        
    # Check if config exists
    if not (PROJECT_ROOT / 'config' / 'settings.py').exists():
        print("❌ Error: Configuration not found")
        print("   Please ensure config/settings.py exists")
        return False
        
    # Check and report Python environment
    python_exe = find_venv_python()
    if python_exe:
        print(f"🐍 Using Python: {python_exe}")
        
    return True

def main():
    """Main entry point"""
    print_header()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Parse arguments
    if len(sys.argv) == 1:
        # No arguments - start full system (trading + dashboard)
        print("🚀 Starting WawaTrader Full System (trading + dashboard)")
        print("   Use 'python start.py menu' to see all options")
        print("   Use 'python start.py help' for detailed help")
        print("   Dashboard: http://localhost:8050")
        print("   Note: Dashboard may show warnings (safe to ignore)")
        print()
        cmd = 'full'
        args = []
    else:
        cmd = sys.argv[1].lower()
        args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Handle special commands first
    if cmd in ['help', '--help', '-h']:
        print_help()
        return
    elif cmd in ['menu', '--menu', '-m']:
        print_menu()
        return
    
    # Run the command
    success = run_command(cmd, args)
    
    if success:
        print(f"\n✅ {cmd} completed successfully")
    else:
        print(f"\n❌ {cmd} failed or was interrupted")
        sys.exit(1)

if __name__ == '__main__':
    main()