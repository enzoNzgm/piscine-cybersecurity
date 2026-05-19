# Stockholm - Ransomware for Educational Purposes

An encryption/decryption utility that encrypts files matching Wannacry-affected extensions.

## Installation

```bash
make
```

## Usage

```bash
./stockholm              # Encrypt files in ~/infection/
./stockholm -s           # Silent mode: encrypt without printing filenames
./stockholm -r KEY       # Decrypt files using KEY
./stockholm --help       # Show help
./stockholm --version    # Show version
```

## Encryption Algorithm

**Fernet (AES-128 in CBC mode)** - A secure, authenticated encryption method from the `cryptography` library.

Key derivation uses **PBKDF2 with SHA256** (480,000 iterations) to strengthen passwords.

### Why Fernet?
- Industry-standard symmetric encryption
- Built-in HMAC for authentication
- Protection against tampering
- Time-stamped ciphertexts

## File Extensions Targeted

Wannacry-affected extensions: .docx, .xlsx, .pptx, .pdf, .jpg, .png, .txt, .sql, .zip, .rar, and others.

## Features

- Encrypts files in `~/infection/` directory
- Adds `.ft` extension to encrypted files
- Generates secure random 16-character keys
- Full error handling
- Silent mode support


