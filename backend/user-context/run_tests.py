#!/usr/bin/env python3
"""
DelegateProfile Test Runner

This script provides an easy way to run different tests of your DelegateProfile system.
It allows you to:
1. Test the environment setup and Supabase connection
2. Run a full integration test
3. Run the example delegate profile script
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_module_from_file(file_path):
    """Import a module from a file path."""
    try:
        module_name = Path(file_path).stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error importing {file_path}: {e}")
        return None

def print_menu():
    """Print the test menu options."""
    print("\n===== DelegateProfile Test Runner =====")
    print("1. Test environment and Supabase connection")
    print("2. Run full integration test")
    print("3. Run example script")
    print("4. View system info")
    print("5. Exit")
    return input("\nEnter your choice (1-5): ")

def check_dependencies():
    """Check if all required dependencies are installed."""
    dependencies = {
        'supabase': False,
        'dotenv': False,
    }
    
    try:
        import supabase
        dependencies['supabase'] = True
    except ImportError:
        pass
    
    try:
        import dotenv
        dependencies['dotenv'] = True
    except ImportError:
        pass
    
    return dependencies

def print_system_info():
    """Print information about the system setup."""
    print("\n===== System Information =====")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check current directory
    print(f"Current directory: {os.getcwd()}")
    
    # Check if key files exist
    files_to_check = [
        "delegate_profile.py",
        "test_integration.py",
        "example_delegate_profile.py",
        ".env"
    ]
    
    print("\nFile availability:")
    for file in files_to_check:
        exists = os.path.exists(file)
        print(f"  {file}: {'✅ Found' if exists else '❌ Not found'}")
    
    # Check dependencies
    deps = check_dependencies()
    print("\nDependencies:")
    for dep, installed in deps.items():
        print(f"  {dep}: {'✅ Installed' if installed else '❌ Not installed'}")
    
    # Check environment variables
    env_vars = {
        "NEXT_PUBLIC_SUPABASE_URL": os.environ.get("NEXT_PUBLIC_SUPABASE_URL"),
        "NEXT_PUBLIC_SUPABASE_ANON_KEY": os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    }
    
    print("\nEnvironment variables:")
    for var, value in env_vars.items():
        if value:
            # Show partial value for security
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            print(f"  {var}: ✅ Set ({masked})")
        else:
            print(f"  {var}: ❌ Not set")

def main():
    """Main function to run tests based on user input."""
    while True:
        choice = print_menu()
        
        if choice == '1':
            # Test environment and connection
            logger.info("Testing environment and Supabase connection...")
            test_integration = import_module_from_file("test_integration.py")
            if test_integration:
                test_integration.check_environment()
                test_integration.test_supabase_connection()
        
        elif choice == '2':
            # Run full integration test
            logger.info("Running full integration test...")
            test_integration = import_module_from_file("test_integration.py")
            if test_integration:
                test_integration.main()
        
        elif choice == '3':
            # Run example script
            logger.info("Running example delegate profile script...")
            example = import_module_from_file("example_delegate_profile.py")
            if example:
                example.main()
        
        elif choice == '4':
            # View system info
            print_system_info()
        
        elif choice == '5':
            # Exit
            print("Exiting. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")
        
        # Pause before showing menu again
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 