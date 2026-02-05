# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-02-05

### Added

- Initial release
- Auto-discovery of all Apple Mail accounts
- Support for IMAP, Exchange, POP, iCloud, and Local accounts
- Export to native Apple Mail format (for restoration)
- Export to standard mbox format (for portability)
- Interactive account selection
- Command-line options for non-interactive use
- Detailed backup summaries and reports
- Human-readable account names (resolved from macOS Accounts database)
- Colored terminal output
- Progress indicators during backup

### Supported Account Types

- Gmail (IMAP)
- Outlook/Hotmail (Exchange)
- iCloud Mail
- Yahoo Mail
- Corporate Exchange servers
- Any standard IMAP/POP server
- Local "On My Mac" mailboxes

### Output Formats

- `Mail_Raw_Data/`: Apple Mail's native emlx format
- `mbox_format/`: Standard Unix mbox format (RFC 4155 compliant)

### Notes

- Created with assistance from Claude (Anthropic)
