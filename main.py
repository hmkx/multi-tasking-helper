"""
Main entry point for MultiTask Helper.
Clean, simple launcher with command-line options.
"""

import argparse
import sys
from pathlib import Path

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="MultiTask Helper - AI-powered window switching assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--console",
        action="store_true",
        help="Run in console mode (no GUI)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="MultiTask Helper v0.1"
    )
    
    return parser.parse_args()


def run_console_mode():
    """Run in console mode"""
    from controller import MultitaskController
    
    print("="*60)
    print("MULTITASK HELPER - CONSOLE MODE")
    print("="*60)
    print("Press Ctrl+C to exit")
    print()
    
    controller = MultitaskController(enable_llm=True)
    
    def on_suggestions(suggestions):
        if suggestions:
            print(f"\nSuggestions ({len(suggestions)}):")
            for i, (reason, window, confidence) in enumerate(suggestions, 1):
                print(f"  {i}. {reason}: {window.process_name} - {confidence}")
        else:
            print("\nNo suggestions available")
    
    controller.set_callbacks(on_suggestions_ready=on_suggestions)
    controller.start_monitoring()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        controller.stop_monitoring()


def run_gui_mode():
    """Run in GUI mode"""
    try:
        from gui import create_gui
        
        print("Starting MultiTask Helper GUI...")
        app = create_gui(enable_llm=True)
        app.run()
        
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Falling back to console mode...")
        run_console_mode()
    except Exception as e:
        print(f"GUI error: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Show startup info
    print("MultiTask Helper v0.1")
    print("LLM: Enabled")
    print()
    
    # Run appropriate mode
    if args.console:
        run_console_mode()
    else:
        run_gui_mode()


if __name__ == "__main__":
    main()