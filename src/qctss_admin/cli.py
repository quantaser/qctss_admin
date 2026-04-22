"""
Command line interface for qctss-admin
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from .client import RCCIAdmin, PermissionError, BillingClientError, InvalidBillingPeriodError
from .__init__ import __version__


def main() -> int:
    """
    Main CLI entry point
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        prog="qctss-admin",
        description="QCTSS Admin SDK command line interface"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"qctss-admin {__version__}"
    )
    
    parser.add_argument(
        "--token",
        required=True,
        help="Admin JWT authentication token"
    )
    
    parser.add_argument(
        "--backend-url",
        help="Backend API URL (overrides config)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Billing download command
    billing_parser = subparsers.add_parser("download-billing", help="Download billing CSV")
    billing_parser.add_argument("year", type=int, help="Billing year")
    billing_parser.add_argument("month", type=int, help="Billing month (1-12)")
    billing_parser.add_argument(
        "--output", 
        help="Output file path (default: print to stdout)"
    )
    
    # Billing summary command
    summary_parser = subparsers.add_parser("billing-summary", help="Get billing summary")
    summary_parser.add_argument("year", type=int, help="Billing year")
    summary_parser.add_argument("month", type=int, help="Billing month (1-12)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Initialize admin client
        admin = RCCIAdmin(
            token=args.token,
            backend_url=args.backend_url
        )
        
        if args.command == "download-billing":
            # Download billing CSV
            try:
                result = admin.download_billing_csv(
                    year=args.year,
                    month=args.month,
                    output_file=args.output
                )
                
                if args.output:
                    print(f"Billing CSV saved to: {result}")
                else:
                    print(result)  # Print CSV content
                    
            except (InvalidBillingPeriodError, BillingClientError) as e:
                print(f"Billing error: {e}", file=sys.stderr)
                return 1
        
        elif args.command == "billing-summary":
            # Get billing summary
            try:
                summary = admin.get_billing_summary(args.year, args.month)
                
                print(f"Billing Summary for {args.year}-{args.month:02d}:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
                    
            except (InvalidBillingPeriodError, BillingClientError) as e:
                print(f"Billing error: {e}", file=sys.stderr)
                return 1
        
        admin.close()
        return 0
        
    except PermissionError as e:
        print(f"Permission error: {e}", file=sys.stderr)
        return 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())