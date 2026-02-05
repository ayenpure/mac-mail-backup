"""
Core backup functionality for Mac Mail.
"""

import os
import sys
import re
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from collections import defaultdict
from typing import Dict, List, Optional, Any

from .converter import MboxConverter


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


def colorize(text: str, color_code: str) -> str:
    """Apply color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{color_code}{text}{Colors.END}"
    return text


class MacMailBackup:
    """
    Main backup class for Apple Mail on macOS.

    This class handles:
    - Discovering mail accounts from the Mail.app data
    - Identifying account types (IMAP, Exchange, Local)
    - Resolving account email addresses
    - Backing up to native and mbox formats
    """

    def __init__(self, output_dir: Optional[str] = None, verbose: bool = True):
        """
        Initialize the backup tool.

        Args:
            output_dir: Directory for backup output. Defaults to current directory.
            verbose: If True, print progress information.
        """
        self.mail_dir = Path.home() / "Library" / "Mail"
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.verbose = verbose
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.mail_version: Optional[Path] = None
        self.envelope_db: Optional[sqlite3.Connection] = None
        self.converter = MboxConverter(verbose=verbose)

    def _print(self, message: str, end: str = '\n', flush: bool = False) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message, end=end, flush=flush)

    def find_mail_version(self) -> Path:
        """
        Find the Mail data version directory (V10, V9, etc.).

        Returns:
            Path to the Mail version directory.

        Raises:
            FileNotFoundError: If Mail directory or version not found.
        """
        if not self.mail_dir.exists():
            raise FileNotFoundError(
                f"Mail directory not found: {self.mail_dir}\n"
                "Make sure Apple Mail is configured on this system."
            )

        # Find version directories (V10, V9, etc.)
        versions = sorted(
            [d for d in self.mail_dir.iterdir() if d.is_dir() and d.name.startswith('V')],
            key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else 0,
            reverse=True
        )

        if not versions:
            raise FileNotFoundError(
                "No Mail version directory found (V10, V9, etc.)\n"
                "Make sure Apple Mail has been used at least once."
            )

        self.mail_version = versions[0]
        self._print(f"Found Mail data: {colorize(str(self.mail_version), Colors.CYAN)}")
        return self.mail_version

    def discover_accounts(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all mail accounts and their details.

        Returns:
            Dictionary mapping account UUIDs to account information.
        """
        if not self.mail_version:
            self.find_mail_version()

        # Open the Envelope Index database
        envelope_path = self.mail_version / "MailData" / "Envelope Index"
        if not envelope_path.exists():
            raise FileNotFoundError(f"Envelope Index not found: {envelope_path}")

        self.envelope_db = sqlite3.connect(str(envelope_path))

        # Get unique accounts from mailbox URLs
        cursor = self.envelope_db.cursor()
        cursor.execute("""
            SELECT DISTINCT
                CASE
                    WHEN url LIKE 'imap://%' THEN 'IMAP'
                    WHEN url LIKE 'ews://%' THEN 'Exchange'
                    WHEN url LIKE 'local://%' THEN 'Local'
                    WHEN url LIKE 'pop://%' THEN 'POP'
                    ELSE 'Other'
                END as type,
                substr(url, instr(url, '//')+2, 36) as account_uuid,
                url
            FROM mailboxes
            WHERE url LIKE '%://%'
        """)

        account_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'type': '', 'uuid': '', 'mailboxes': [], 'path': None}
        )

        for row in cursor.fetchall():
            acc_type, uuid, url = row
            if uuid and len(uuid) == 36:  # Valid UUID format
                account_data[uuid]['type'] = acc_type
                account_data[uuid]['uuid'] = uuid
                # Extract mailbox path from URL
                if '/' in url:
                    mailbox_path = unquote(url.split('/', 3)[-1]) if url.count('/') >= 3 else ''
                    if mailbox_path and mailbox_path not in account_data[uuid]['mailboxes']:
                        account_data[uuid]['mailboxes'].append(mailbox_path)

        # Find actual directories and resolve email addresses
        for uuid, data in account_data.items():
            account_path = self.mail_version / uuid
            if account_path.exists():
                data['path'] = account_path
                data['email'] = self._resolve_account_email(uuid, data['type'])
                data['display_name'] = self._generate_display_name(data)

        self.accounts = dict(account_data)
        return self.accounts

    def _resolve_account_email(self, uuid: str, acc_type: str) -> str:
        """
        Resolve the email address for an account.

        Uses macOS Accounts database for reliable account identification.

        Args:
            uuid: The account UUID.
            acc_type: The account type (IMAP, Exchange, etc.).

        Returns:
            The email address or a descriptive fallback.
        """
        # Try macOS Accounts database (most reliable source)
        accounts_db_path = Path.home() / "Library" / "Accounts" / "Accounts4.sqlite"
        if accounts_db_path.exists():
            try:
                accounts_db = sqlite3.connect(str(accounts_db_path))
                cursor = accounts_db.cursor()

                # Query for account info including parent account
                cursor.execute("""
                    SELECT
                        z.ZACCOUNTDESCRIPTION,
                        z.ZUSERNAME,
                        p.ZACCOUNTDESCRIPTION as parent_desc,
                        p.ZUSERNAME as parent_user
                    FROM ZACCOUNT z
                    LEFT JOIN ZACCOUNT p ON z.ZPARENTACCOUNT = p.Z_PK
                    WHERE z.ZIDENTIFIER = ?
                """, (uuid,))

                row = cursor.fetchone()
                accounts_db.close()

                if row:
                    desc, username, parent_desc, parent_user = row

                    # Prefer direct username with @, then parent username
                    if username and '@' in str(username):
                        return username
                    if parent_user and '@' in str(parent_user):
                        return parent_user

                    # Use description if it looks like an email or account name
                    if desc and desc not in ('', 'On My Mac'):
                        return desc
                    if parent_desc and parent_desc not in ('', 'On My Mac'):
                        return parent_desc

            except Exception:
                pass  # Fall through to fallback methods

        # Fallback: return generic type-based name
        type_names = {
            'IMAP': 'IMAP Account',
            'Exchange': 'Exchange Account',
            'POP': 'POP Account',
            'Local': 'Local Account',
        }
        return type_names.get(acc_type, f'{acc_type} Account')

    def _generate_display_name(self, data: Dict[str, Any]) -> str:
        """
        Generate a human-readable display name for an account.

        Args:
            data: Account data dictionary.

        Returns:
            Formatted display name.
        """
        email = data.get('email', '')
        acc_type = data.get('type', 'Unknown')

        if '@' in email:
            # Determine provider from email domain
            domain = email.split('@')[1].lower()

            # Common email providers
            provider_map = {
                'gmail.com': 'Gmail',
                'googlemail.com': 'Gmail',
                'outlook.com': 'Outlook',
                'hotmail.com': 'Hotmail',
                'live.com': 'Outlook',
                'msn.com': 'MSN',
                'icloud.com': 'iCloud',
                'me.com': 'iCloud',
                'mac.com': 'iCloud',
                'yahoo.com': 'Yahoo',
                'aol.com': 'AOL',
                'protonmail.com': 'ProtonMail',
                'proton.me': 'ProtonMail',
                'fastmail.com': 'Fastmail',
                'zoho.com': 'Zoho',
            }

            provider = provider_map.get(domain)
            if not provider:
                # Use domain name as provider (e.g., company.com -> Company)
                provider = domain.split('.')[0].title()

            return f"{provider} ({acc_type}) - {email}"

        elif email and email not in ('Local Account', 'IMAP Account', 'Exchange Account', 'POP Account'):
            return f"{email} ({acc_type})"

        return f"{acc_type} Account ({data['uuid'][:8]}...)"

    def list_accounts(self) -> List[str]:
        """
        Print discovered accounts in a user-friendly format.

        Returns:
            List of account UUIDs.
        """
        if not self.accounts:
            self.discover_accounts()

        self._print(f"\n{colorize('═' * 60, Colors.BLUE)}")
        self._print(colorize("  DISCOVERED MAIL ACCOUNTS", Colors.BOLD))
        self._print(f"{colorize('═' * 60, Colors.BLUE)}\n")

        valid_accounts = []
        for i, (uuid, data) in enumerate(self.accounts.items(), 1):
            if data['path'] and data['path'].exists():
                valid_accounts.append(uuid)
                email_count = self._count_emails(data['path'])
                size = self._get_dir_size(data['path'])

                self._print(f"  {colorize(f'[{len(valid_accounts)}]', Colors.GREEN)} "
                           f"{colorize(data['display_name'], Colors.BOLD)}")
                self._print(f"      Type: {data['type']}")
                self._print(f"      Emails: ~{email_count:,}")
                self._print(f"      Size: {self._format_size(size)}")
                self._print(f"      Folders: {len(data['mailboxes'])}")
                self._print("")

        return valid_accounts

    def _count_emails(self, path: Path) -> int:
        """Count emlx files in a directory."""
        count = 0
        for root, dirs, files in os.walk(path):
            count += sum(1 for f in files if f.endswith('.emlx'))
        return count

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of a directory in bytes."""
        total = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total

    def _format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def select_accounts_interactive(self, account_uuids: List[str]) -> List[str]:
        """
        Interactive account selection via terminal.

        Args:
            account_uuids: List of available account UUIDs.

        Returns:
            List of selected account UUIDs.
        """
        self._print(f"\n{colorize('Select accounts to backup:', Colors.YELLOW)}")
        self._print("  Enter numbers separated by commas (e.g., 1,2)")
        self._print("  Or 'all' to backup everything")
        self._print("  Or 'q' to quit\n")

        while True:
            try:
                choice = input(f"{colorize('Your choice: ', Colors.CYAN)}").strip().lower()

                if choice == 'q':
                    self._print("Backup cancelled.")
                    sys.exit(0)

                if choice == 'all':
                    return account_uuids

                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected = [account_uuids[i] for i in indices if 0 <= i < len(account_uuids)]

                if selected:
                    return selected
                self._print(colorize("Invalid selection. Please try again.", Colors.RED))

            except (ValueError, IndexError):
                self._print(colorize("Invalid input. Enter numbers separated by commas.", Colors.RED))

    def backup_account(self, uuid: str, backup_dir: Path) -> bool:
        """
        Backup a single account.

        Args:
            uuid: Account UUID.
            backup_dir: Base backup directory.

        Returns:
            True if backup succeeded, False otherwise.
        """
        data = self.accounts.get(uuid)
        if not data or not data['path'] or not data['path'].exists():
            self._print(f"  {colorize('✗', Colors.RED)} Account path not found")
            return False

        # Create safe directory name from email
        email = data.get('email', '')
        if '@' in email:
            account_name = email.replace('@', '_at_').replace('.', '_')
        else:
            account_name = f"{data['type']}_{uuid[:8]}"

        # Sanitize for filesystem
        account_name = re.sub(r'[^\w\-_]', '_', account_name)
        account_backup_dir = backup_dir / account_name

        self._print(f"\n  Backing up: {colorize(data['display_name'], Colors.BOLD)}")

        # Create backup directory
        account_backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy raw Mail data
        raw_dir = account_backup_dir / "Mail_Raw_Data"
        self._print(f"    Copying raw data...", end=' ', flush=True)
        try:
            shutil.copytree(data['path'], raw_dir, dirs_exist_ok=True)
            self._print(colorize("✓", Colors.GREEN))
        except Exception as e:
            self._print(colorize(f"✗ {e}", Colors.RED))
            return False

        # 2. Convert to mbox format
        mbox_dir = account_backup_dir / "mbox_format"
        mbox_dir.mkdir(exist_ok=True)
        self._print(f"    Converting to mbox format...")
        email_counts = self.converter.convert_account(str(raw_dir), str(mbox_dir))

        # 3. Generate account summary
        self._write_account_summary(account_backup_dir, data, email_counts)

        return True

    def _write_account_summary(
        self,
        backup_dir: Path,
        account_data: Dict[str, Any],
        email_counts: Dict[str, int]
    ) -> None:
        """Write a summary file for the account backup."""
        summary_path = backup_dir / "BACKUP_INFO.txt"

        total_emails = sum(email_counts.values())
        raw_size = self._get_dir_size(backup_dir / "Mail_Raw_Data")
        mbox_size = self._get_dir_size(backup_dir / "mbox_format")

        with open(summary_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write(f"  MAIL BACKUP: {account_data.get('email', 'Unknown')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Backup Date:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Account Type:    {account_data['type']}\n")
            f.write(f"Account UUID:    {account_data['uuid']}\n")
            f.write(f"Total Emails:    {total_emails:,}\n")
            f.write(f"Raw Data Size:   {self._format_size(raw_size)}\n")
            f.write(f"Mbox Size:       {self._format_size(mbox_size)}\n\n")

            f.write("FOLDER BREAKDOWN:\n")
            f.write("-" * 40 + "\n")
            for folder, count in sorted(email_counts.items()):
                f.write(f"  {folder}: {count:,} emails\n")

            f.write("\n" + "=" * 60 + "\n")

    def _write_master_summary(self, backup_dir: Path, selected_uuids: List[str]) -> None:
        """Write master summary for the entire backup."""
        summary_path = backup_dir / "BACKUP_SUMMARY.txt"

        with open(summary_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("  MAC MAIL BACKUP SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Backup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Size:  {self._format_size(self._get_dir_size(backup_dir))}\n\n")

            f.write("ACCOUNTS BACKED UP:\n")
            f.write("-" * 40 + "\n")
            for uuid in selected_uuids:
                if uuid in self.accounts:
                    data = self.accounts[uuid]
                    f.write(f"  - {data['display_name']}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("""
RESTORATION INSTRUCTIONS:
-------------------------

To restore to Mac Mail:
1. Quit the Mail app completely
2. Copy the Mail_Raw_Data folder contents back to:
   ~/Library/Mail/V10/[ACCOUNT-UUID]/
3. Relaunch Mail and let it rebuild indexes

To import mbox files to other email clients:
- Thunderbird: Use ImportExportTools NG addon
- Outlook: Use third-party mbox import tools
- Most email clients support standard mbox format

Note: The mbox files are in standard Unix mbox format
and can be read by most email applications.
""")

    def run(self, selected_uuids: Optional[List[str]] = None) -> Optional[Path]:
        """
        Run the complete backup process.

        Args:
            selected_uuids: Optional list of account UUIDs to backup.
                           If None, will prompt for interactive selection.

        Returns:
            Path to backup directory, or None if cancelled.
        """
        self._print(f"\n{colorize('╔' + '═' * 58 + '╗', Colors.BLUE)}")
        self._print(f"{colorize('║', Colors.BLUE)}  "
                   f"{colorize('MAC MAIL BACKUP TOOL', Colors.BOLD)}"
                   f"{' ' * 36}{colorize('║', Colors.BLUE)}")
        self._print(f"{colorize('╚' + '═' * 58 + '╝', Colors.BLUE)}\n")

        # Discover accounts
        self._print(colorize("Scanning for mail accounts...", Colors.YELLOW))
        self.discover_accounts()

        # List and select accounts
        account_uuids = self.list_accounts()

        if not account_uuids:
            self._print(colorize("No mail accounts found!", Colors.RED))
            return None

        # Select accounts if not provided
        if selected_uuids is None:
            selected_uuids = self.select_accounts_interactive(account_uuids)

        # Validate selected UUIDs
        selected_uuids = [u for u in selected_uuids if u in self.accounts]
        if not selected_uuids:
            self._print(colorize("No valid accounts selected.", Colors.RED))
            return None

        # Create backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.output_dir / f"Mail_Backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        self._print(f"\n{colorize('Starting backup...', Colors.GREEN)}")
        self._print(f"Output directory: {colorize(str(backup_dir), Colors.CYAN)}")

        # Backup each selected account
        successful = 0
        for uuid in selected_uuids:
            if self.backup_account(uuid, backup_dir):
                successful += 1

        # Write master summary
        self._write_master_summary(backup_dir, selected_uuids)

        # Final report
        self._print(f"\n{colorize('═' * 60, Colors.GREEN)}")
        self._print(colorize("  BACKUP COMPLETE!", Colors.BOLD + Colors.GREEN))
        self._print(f"{colorize('═' * 60, Colors.GREEN)}")
        self._print(f"\n  Accounts backed up: {successful}/{len(selected_uuids)}")
        self._print(f"  Location: {backup_dir}")
        self._print(f"  Total size: {self._format_size(self._get_dir_size(backup_dir))}")
        self._print("")

        return backup_dir
