# Mac Mail Backup

[![PyPI version](https://badge.fury.io/py/mac-mail-backup.svg)](https://badge.fury.io/py/mac-mail-backup)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A command-line tool for backing up Apple Mail accounts to portable formats on macOS.

## Features

- **Auto-discovery**: Automatically finds all configured mail accounts (Gmail, Outlook, iCloud, Exchange, IMAP, POP, etc.)
- **Human-readable**: Shows account names and email addresses instead of cryptic UUIDs
- **Dual format export**:
  - Native Apple Mail format (for restoring to Mail.app)
  - Standard mbox format (portable, works with Thunderbird, Outlook, and other email clients)
- **Selective backup**: Choose which accounts to backup interactively or via command line
- **Zero dependencies**: Pure Python, no external packages required
- **Detailed summaries**: Generates backup reports with email counts and folder breakdowns

## Installation

### From PyPI (recommended)

```bash
pip install mac-mail-backup
```

### From source

```bash
git clone https://github.com/ayenpure/mac-mail-backup.git
cd mac-mail-backup
pip install -e .
```

## Quick Start

### List available accounts

```bash
mac-mail-backup --list
```

Output:
```
════════════════════════════════════════════════════════════
  DISCOVERED MAIL ACCOUNTS
════════════════════════════════════════════════════════════

  [1] Gmail (IMAP) - john.doe@gmail.com
      Type: IMAP
      Emails: ~15,432
      Size: 2.3 GB
      Folders: 12

  [2] Outlook (Exchange) - john.doe@company.com
      Type: Exchange
      Emails: ~8,921
      Size: 1.1 GB
      Folders: 8

  [3] iCloud (IMAP) - john@icloud.com
      Type: IMAP
      Emails: ~3,456
      Size: 456.2 MB
      Folders: 5
```

### Interactive backup

```bash
mac-mail-backup
```

This will prompt you to select which accounts to backup.

### Backup specific accounts

```bash
# Backup account #1
mac-mail-backup -a 1

# Backup accounts #1 and #2
mac-mail-backup -a 1,2

# Backup all accounts
mac-mail-backup --all
```

### Specify output directory

```bash
mac-mail-backup -a 1 -o ~/Backups

# Or using positional argument
mac-mail-backup ~/Backups -a 1
```

## Command Line Options

```
usage: mac-mail-backup [-h] [-o DIR] [-l] [-a NUM] [--all] [-q] [-v] [output_dir]

Backup Apple Mail accounts to portable formats (mbox)

positional arguments:
  output_dir           Output directory for backup (default: current directory)

options:
  -h, --help           show this help message and exit
  -o, --output DIR     Output directory for backup
  -l, --list           List available mail accounts and exit
  -a, --account NUM    Account number(s) to backup (comma-separated)
  --all                Backup all accounts without prompting
  -q, --quiet          Suppress progress output
  -v, --version        show program's version number and exit
```

## Output Structure

Each backup creates a timestamped directory with the following structure:

```
Mail_Backup_20240115_143052/
├── BACKUP_SUMMARY.txt           # Overall backup summary
├── john_doe_at_gmail_com/       # Per-account directory
│   ├── BACKUP_INFO.txt          # Account backup details
│   ├── Mail_Raw_Data/           # Apple Mail native format
│   │   ├── INBOX.mbox/
│   │   ├── [Gmail].mbox/
│   │   │   ├── All Mail.mbox/
│   │   │   ├── Sent Mail.mbox/
│   │   │   └── ...
│   │   └── ...
│   └── mbox_format/             # Portable mbox files
│       ├── INBOX.mbox
│       ├── Gmail_All_Mail.mbox
│       ├── Gmail_Sent_Mail.mbox
│       └── ...
└── john_doe_at_company_com/
    └── ...
```

## Restoring Backups

### To Apple Mail

1. Quit Mail.app completely
2. Copy the `Mail_Raw_Data` folder contents to:
   ```
   ~/Library/Mail/V10/[ACCOUNT-UUID]/
   ```
3. Relaunch Mail and let it rebuild indexes

### To Other Email Clients

The `mbox_format/` directory contains standard Unix mbox files that can be imported into:

- **Thunderbird**: Use the [ImportExportTools NG](https://addons.thunderbird.net/addon/importexporttools-ng/) addon
- **Outlook**: Use third-party mbox import tools
- **Most other email clients**: Standard mbox format is widely supported

## Requirements

- **macOS** (tested on macOS 12+)
- **Python 3.8+**
- **Apple Mail** must be configured with at least one account

## How It Works

1. **Account Discovery**: Reads from macOS Accounts database and Mail's Envelope Index to find configured accounts
2. **Email Resolution**: Maps account UUIDs to human-readable email addresses
3. **Data Export**: Copies Apple Mail's native emlx files and converts them to standard mbox format
4. **Mbox Conversion**: Parses emlx files (Apple's proprietary format) and writes RFC-compliant mbox files

## Supported Account Types

- IMAP (Gmail, Yahoo, Fastmail, custom IMAP servers, etc.)
- Exchange (Microsoft 365, Outlook.com, corporate Exchange)
- iCloud Mail
- POP3
- Local/On My Mac

## Privacy & Security

- All data stays on your local machine
- No network connections are made
- No data is sent anywhere
- Works completely offline

## Troubleshooting

### "Mail directory not found"

Make sure Apple Mail is installed and has been opened at least once.

### "No mail accounts found"

Ensure you have at least one email account configured in Mail.app (System Preferences → Internet Accounts).

### Permission errors

The tool needs read access to:
- `~/Library/Mail/` - Mail data
- `~/Library/Accounts/` - Account information

On newer macOS versions, you may need to grant Terminal/iTerm Full Disk Access in System Preferences → Security & Privacy → Privacy.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Apple Mail's emlx format documentation from various reverse-engineering efforts
- The mbox format specification (RFC 4155)
- Created with assistance from [Claude](https://www.anthropic.com/claude) (Anthropic)

## Author

**Abhishek Yenpure** - [GitHub](https://github.com/ayenpure)

---

*Made with assistance from Claude (Anthropic) for the macOS community*
