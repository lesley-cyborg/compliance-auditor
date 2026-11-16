import argparse
import sys
import os
from dotenv import load_dotenv

# Import our core modules
from ingest import ingest_csv
from evaluate import evaluate_devices
from alert import alert

# Load environment variables at the entry point
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="Automated Endpoint Compliance Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run --file mock_inventory.csv   # Run the full pipeline
  python main.py ingest --file mock_inventory.csv # Only ingest data
  python main.py evaluate                        # Only evaluate policy
  python main.py alert                           # Only check and send alerts
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 1. Run Command (Full Pipeline)
    run_parser = subparsers.add_parser("run", help="Run the full compliance pipeline")
    run_parser.add_argument("--file", required=True, help="Path to the CSV inventory file")

    # 2. Ingest Command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest CSV data into the database")
    ingest_parser.add_argument("--file", required=True, help="Path to the CSV inventory file")

    # 3. Evaluate Command
    subparsers.add_parser("evaluate", help="Evaluate devices against the security policy")

    # 4. Alert Command
    subparsers.add_parser("alert", help="Check for non-compliant devices and send alerts")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print(f".... Starting Compliance Auditor: {args.command.upper()}")
    print("=" * 60)

    try:
        if args.command == "run":
            print("\n[1/3]. Ingesting data...")
            ingest_csv(args.file)
            
            print("\n[2/3].. Evaluating policy...")
            evaluate_devices()
            
            print("\n[3/3]... Checking alerts...")
            alert()
            
            print("\n.... Full pipeline completed successfully!")

        elif args.command == "ingest":
            ingest_csv(args.file)

        elif args.command == "evaluate":
            evaluate_devices()

        elif args.command == "alert":
            alert()

    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()