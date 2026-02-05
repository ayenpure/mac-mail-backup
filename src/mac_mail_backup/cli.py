"""
Command-line interface for Mac Mail Backup.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from . import __version__
from .backup import MacMailBackup, colorize, Colors


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog='mac-mail-backup',
        description='Backup Apple Mail accounts to portable formats (mbox)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mac-mail-backup                    Interactive mode, backup to current directory
  mac-mail-backup ~/Backups          Backup to specified directory
  mac-mail-backup --list             List available accounts
  mac-mail-backup -a 1               Backup account #1
  mac-mail-backup -a 1,2             Backup accounts #1 and #2
  mac-mail-backup --all              Backup all accounts
  mac-mail-backup -a 2 -o ~/Backups  Backup account #2 to ~/Backups

Output Formats:
  The backup creates two formats for each account:

  1. Mail_Raw_Data/  - Apple Mail's native format (for restoring to Mail.app)
  2. mbox_format/    - Standard mbox files (portable, works with most email clients)

More Information:
  https://github.com/ayenpure/mac-mail-backup
        """
    )

    parser.add_argument(
        'output_dir',
        nargs='?',
        default=None,
        help='Output directory for backup (default: current directory)'
    )

    parser.add_argument(
        '-o', '--output',
        dest='output_dir_flag',
        metavar='DIR',
        help='Output directory for backup (alternative to positional argument)'
    )

    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List available mail accounts and exit'
    )

    parser.add_argument(
        '-a', '--account',
        type=str,
        metavar='NUM',
        help='Account number(s) to backup (comma-separated, e.g., 1,2,3)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Backup all accounts without prompting'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress output (only show errors)'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parsed = parse_args(args)

    # Determine output directory
    output_dir = parsed.output_dir_flag or parsed.output_dir

    try:
        backup = MacMailBackup(
            output_dir=output_dir,
            verbose=not parsed.quiet
        )

        if parsed.list:
            # Just list accounts
            backup.discover_accounts()
            backup.list_accounts()
            return 0

        if parsed.all or parsed.account:
            # Non-interactive mode
            backup.discover_accounts()
            account_uuids = backup.list_accounts()

            if not account_uuids:
                print(colorize("No mail accounts found.", Colors.RED), file=sys.stderr)
                return 1

            if parsed.all:
                selected = account_uuids
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in parsed.account.split(',')]
                    selected = [account_uuids[i] for i in indices if 0 <= i < len(account_uuids)]
                except (ValueError, IndexError):
                    print(colorize(f"Invalid account selection: {parsed.account}", Colors.RED),
                          file=sys.stderr)
                    return 1

            if not selected:
                print(colorize("No valid accounts selected.", Colors.RED), file=sys.stderr)
                return 1

            result = backup.run(selected)
            return 0 if result else 1

        else:
            # Interactive mode
            result = backup.run()
            return 0 if result else 1

    except FileNotFoundError as e:
        print(colorize(f"Error: {e}", Colors.RED), file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print(colorize("\n\nBackup cancelled by user.", Colors.YELLOW), file=sys.stderr)
        return 130

    except Exception as e:
        print(colorize(f"Unexpected error: {e}", Colors.RED), file=sys.stderr)
        if not parsed.quiet:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
