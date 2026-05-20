# Stockholm - Ransomware for Educational Purposes

An encryption/decryption utility that encrypts files matching Wannacry-affected extensions.

## Installation

```bash
make
```
- Add your infection directory in the global variable

## Usage

```bash
./stockholm              # Encrypt files in ~/infection/
./stockholm -s           # Silent mode: encrypt without printing filenames
./stockholm -r KEY       # Decrypt files using KEY
./stockholm --help       # Show help
./stockholm --version    # Show version
```

## File Extensions Targeted

Wannacry-affected extensions: .docx, .xlsx, .pptx, .pdf, .jpg, .png, .txt, .sql, .zip, .rar, and others.

## Features

- Encrypts files in `~/infection/` directory
- Adds `.ft` extension to encrypted files
- Generates secure random 16-character keys
- Full error handling
- Silent mode support
