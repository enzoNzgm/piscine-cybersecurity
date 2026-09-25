# ─────────────────────────────────────────────────────────────────────────────
#  Inquisitor — Makefile
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: all build up down clean help attack attack-verbose ftp-test

# Default: build + start everything
all: build up

## Build all Docker images
build:
	docker-compose build

## Start the environment (detached)
up:
	docker-compose up -d
	@echo ""
	@echo "══════════════════════════════════════════════════════════"
	@echo "  Environment started!"
	@echo ""
	@echo "  Containers:"
	@echo "    gateway   172.20.0.1"
	@echo "    victim    172.20.0.2  (FTP client)"
	@echo "    attacker  172.20.0.3  (inquisitor)"
	@echo "    ftpserver 172.20.0.4  (vsftpd)"
	@echo ""
	@echo "  Run the attack:"
	@echo "    make attack"
	@echo ""
	@echo "  Run an FTP test from victim:"
	@echo "    make ftp-test"
	@echo "══════════════════════════════════════════════════════════"

## Launch inquisitor on the attacker container
## Poisons ftpserver <-> victim so FTP traffic is intercepted
attack:
	@echo "[*] Fetching MACs..."
	$(eval MAC_FTP    := $(shell docker exec ftpserver cat /sys/class/net/eth0/address))
	$(eval MAC_VICTIM := $(shell docker exec victim    cat /sys/class/net/eth0/address))
	@echo "    FTPServer 172.20.0.4  $(MAC_FTP)"
	@echo "    Victim    172.20.0.2  $(MAC_VICTIM)"
	@echo "[*] Starting inquisitor (Ctrl+C to stop)..."
	docker exec -it attacker python3 /app/inquisitor.py \
		172.20.0.4 $(MAC_FTP) \
		172.20.0.2 $(MAC_VICTIM)

## Same as attack but with verbose FTP output
attack-verbose:
	@echo "[*] Fetching MACs..."
	$(eval MAC_FTP    := $(shell docker exec ftpserver cat /sys/class/net/eth0/address))
	$(eval MAC_VICTIM := $(shell docker exec victim    cat /sys/class/net/eth0/address))
	docker exec -it attacker python3 /app/inquisitor.py \
		172.20.0.4 $(MAC_FTP) \
		172.20.0.2 $(MAC_VICTIM) -v

## Simulate an FTP session from the victim to the FTP server
ftp-test:
	@echo "[*] Running FTP test from victim -> ftpserver (172.20.0.4)..."
	docker exec victim sh -c 'lftp -u ftpuser,ftppass 172.20.0.4 -e "cd files; ls; get secret.txt; put /etc/hostname -o uploaded.txt; quit"'

## Stop all containers
down:
	docker-compose down

## Remove containers and images
clean:
	docker-compose down --rmi all --volumes --remove-orphans

## Show available targets
help:
	@echo "Targets:"
	@echo "  make          — build + start environment"
	@echo "  make build    — build Docker images"
	@echo "  make up       — start containers"
	@echo "  make attack   — run inquisitor (ARP poison + FTP sniff)"
	@echo "  make attack-verbose — same but with -v flag"
	@echo "  make ftp-test — simulate FTP session from victim"
	@echo "  make down     — stop containers"
	@echo "  make clean    — remove everything"