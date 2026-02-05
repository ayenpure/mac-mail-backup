"""
Mbox format converter for Apple Mail emlx files.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class MboxConverter:
    """Convert Apple Mail emlx files to standard mbox format."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the converter.

        Args:
            verbose: If True, print progress information.
        """
        self.verbose = verbose

    def parse_emlx(self, emlx_path: str) -> Optional[bytes]:
        """
        Parse an emlx file and extract the email content.

        Apple's emlx format consists of:
        1. First line: byte count of the email content
        2. Email content (RFC 2822 format)
        3. Property list with metadata

        Args:
            emlx_path: Path to the emlx file.

        Returns:
            The email content as bytes, or None if parsing failed.
        """
        try:
            with open(emlx_path, 'rb') as f:
                content = f.read()

            # Find the first newline (end of byte count line)
            first_newline = content.find(b'\n')
            if first_newline == -1:
                return None

            # Parse the byte count
            try:
                byte_count = int(content[:first_newline].decode('ascii').strip())
            except (ValueError, UnicodeDecodeError):
                # Fallback: treat remaining content as email
                byte_count = len(content) - first_newline - 1

            # Extract email content
            email_start = first_newline + 1
            return content[email_start:email_start + byte_count]

        except Exception as e:
            if self.verbose:
                print(f"  Warning: Could not parse {emlx_path}: {e}")
            return None

    def get_from_line(self, email_content: bytes) -> str:
        """
        Generate an mbox 'From ' line from email headers.

        The mbox format requires each message to start with a 'From ' line
        containing the sender and date.

        Args:
            email_content: The raw email content.

        Returns:
            A properly formatted 'From ' line.
        """
        try:
            # Extract headers (everything before first blank line)
            header_section = email_content.split(b'\n\n')[0]
            headers = header_section.decode('utf-8', errors='replace')

            # Extract sender
            sender = 'MAILER-DAEMON'
            from_match = re.search(r'^From:\s*(.+?)$', headers, re.MULTILINE | re.IGNORECASE)
            if from_match:
                sender_raw = from_match.group(1).strip()
                # Extract email from "Name <email>" format
                email_match = re.search(r'<([^>]+)>', sender_raw)
                if email_match:
                    sender = email_match.group(1)
                elif '@' in sender_raw:
                    # Plain email address
                    sender = sender_raw.split()[0] if ' ' in sender_raw else sender_raw

            # Extract and format date
            date_formatted = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
            date_match = re.search(r'^Date:\s*(.+?)$', headers, re.MULTILINE | re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1).strip()
                # Try common email date formats
                for fmt in [
                    '%a, %d %b %Y %H:%M:%S %z',
                    '%d %b %Y %H:%M:%S %z',
                    '%a, %d %b %Y %H:%M:%S',
                    '%d %b %Y %H:%M:%S',
                ]:
                    try:
                        dt = datetime.strptime(date_str[:31], fmt)
                        date_formatted = dt.strftime('%a %b %d %H:%M:%S %Y')
                        break
                    except ValueError:
                        continue

            return f"From {sender} {date_formatted}\n"

        except Exception:
            return f"From MAILER-DAEMON {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n"

    def escape_from_lines(self, content: bytes) -> bytes:
        """
        Escape 'From ' at the start of lines in the email body.

        In mbox format, lines starting with 'From ' must be escaped
        to prevent confusion with message separators.

        Args:
            content: The email content.

        Returns:
            Content with 'From ' lines escaped as '>From '.
        """
        lines = content.split(b'\n')
        escaped = []
        for line in lines:
            if line.startswith(b'From '):
                escaped.append(b'>From ' + line[5:])
            else:
                escaped.append(line)
        return b'\n'.join(escaped)

    def find_emlx_files(self, directory: str) -> List[str]:
        """
        Recursively find all emlx files in a directory.

        Args:
            directory: The directory to search.

        Returns:
            Sorted list of emlx file paths.
        """
        emlx_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.emlx') or file.endswith('.partial.emlx'):
                    emlx_files.append(os.path.join(root, file))
        return sorted(emlx_files)

    def convert_folder(self, source_dir: str, mbox_path: str) -> int:
        """
        Convert a Mail folder to mbox format.

        Args:
            source_dir: Source directory containing emlx files.
            mbox_path: Output mbox file path.

        Returns:
            Number of emails converted.
        """
        emlx_files = self.find_emlx_files(source_dir)

        if not emlx_files:
            return 0

        count = 0
        with open(mbox_path, 'wb') as mbox:
            for emlx_path in emlx_files:
                email_content = self.parse_emlx(emlx_path)
                if email_content:
                    from_line = self.get_from_line(email_content)
                    escaped_content = self.escape_from_lines(email_content)

                    mbox.write(from_line.encode('utf-8'))
                    mbox.write(escaped_content)
                    if not escaped_content.endswith(b'\n'):
                        mbox.write(b'\n')
                    mbox.write(b'\n')  # Blank line between messages
                    count += 1

        return count

    def convert_account(self, source_dir: str, output_dir: str) -> Dict[str, int]:
        """
        Convert all mailboxes in an account to mbox format.

        Args:
            source_dir: Source account directory.
            output_dir: Output directory for mbox files.

        Returns:
            Dictionary mapping folder names to email counts.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        email_counts = {}

        # Find all .mbox folders
        mbox_folders: List[Tuple[str, str]] = []
        for root, dirs, files in os.walk(source_dir):
            for d in dirs:
                if d.endswith('.mbox'):
                    mbox_folders.append((os.path.join(root, d), d[:-5]))

        for folder_path, folder_name in mbox_folders:
            # Clean folder name for filename
            clean_name = folder_name.replace('[', '').replace(']', '').replace(' ', '_')
            clean_name = re.sub(r'[^\w\-_]', '_', clean_name)

            # Handle nested folders
            rel_path = os.path.relpath(folder_path, source_dir)
            if '/' in rel_path:
                parts = rel_path.split('/')
                parent = parts[0].replace('.mbox', '').replace('[', '').replace(']', '')
                parent = re.sub(r'[^\w\-_]', '_', parent)
                clean_name = f"{parent}_{clean_name}"

            mbox_path = output_path / f"{clean_name}.mbox"

            if self.verbose:
                print(f"    Converting: {folder_name}...", end=' ', flush=True)

            count = self.convert_folder(folder_path, str(mbox_path))

            if count > 0:
                if self.verbose:
                    print(f"{count:,} emails")
                email_counts[clean_name] = count
            else:
                # Remove empty mbox file
                if mbox_path.exists():
                    mbox_path.unlink()
                if self.verbose:
                    print("(empty)")

        return email_counts
