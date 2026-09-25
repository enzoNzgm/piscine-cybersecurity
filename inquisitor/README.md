# Inquisitor — ARP Poisoning (42 Cybersecurity Piscine)

## Structure

```
inquisitor/
├── inquisitor.py        ← main program
├── Dockerfile.attacker  ← attacker image (Python + libpcap)
├── Dockerfile.ftpserver ← vsftpd FTP server
├── vsftpd.conf          ← FTP server config
├── docker-compose.yaml  ← full test environment
└── Makefile             ← one-command launcher
```

## Usage

```
python3 inquisitor.py <IP-src> <MAC-src> <IP-target> <MAC-target> [-v]
```

| Argument | Description |
|---|---|
| `IP-src` | IP of the source (e.g. gateway) |
| `MAC-src` | MAC of the source |
| `IP-target` | IP of the victim |
| `MAC-target` | MAC of the victim |
| `-v` | Verbose: show ALL FTP traffic (login, responses, commands) |

## What it does

1. **ARP Poisoning (full duplex)** — sends spoofed ARP replies every 2 seconds in both directions so both hosts believe the attacker is the other party.
2. **FTP sniffing** — intercepts TCP port 21 traffic and prints file transfer commands (`RETR`, `STOR`, `DELE`, etc.) in real time.
3. **Clean shutdown** — on `Ctrl+C`, sends 5 genuine ARP replies to both hosts to restore their caches.
4. **Verbose mode** (`-v`) — also shows `USER`, `PASS`, server responses, and all other FTP commands.

## Quick start (Docker)

```bash
# Build and start all containers
make

# In another terminal — launch the attack
make attack

# From victim container — do FTP stuff
make ftp-test
```

## Manual test

```bash
# Build & start
docker compose up -d

# Get MACs
docker exec gateway cat /sys/class/net/eth0/address   # e.g. 02:42:0a:00:00:01
docker exec victim  cat /sys/class/net/eth0/address   # e.g. 02:42:0a:00:00:02

# Run inquisitor
docker exec -it attacker python3 /app/inquisitor.py \
    10.0.0.1 02:42:0a:00:00:01 \
    10.0.0.2 02:42:0a:00:00:02

# In another terminal — FTP session from victim
docker exec victim ftp 10.0.0.4
```

## Requirements

- Linux (raw sockets via `AF_PACKET`)
- Python 3.6+
- Root / `NET_RAW` + `NET_ADMIN` capabilities
- No external Python libraries needed (uses stdlib only)
