#!/bin/bash
# =============================================================
#  SDN Access Control System — Setup & Run Script
# =============================================================
# This script installs dependencies and launches the project.
#
# Usage:
#   chmod +x scripts/setup_and_run.sh
#   sudo ./scripts/setup_and_run.sh [demo|test|controller]
#
# Arguments:
#   demo        → Start topology in interactive Mininet CLI mode
#   test        → Start topology and run automated test suite
#   controller  → Start only the Ryu controller (run topology separately)
# =============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

MODE=${1:-demo}

banner() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║     SDN-Based Access Control System                 ║"
  echo "║     OpenFlow 1.3 + Ryu Controller + Mininet         ║"
  echo "╚══════════════════════════════════════════════════════╝"
  echo -e "${NC}"
}

check_root() {
  if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please run as root (sudo)${NC}"
    exit 1
  fi
}

install_deps() {
  echo -e "${YELLOW}[SETUP] Checking dependencies...${NC}"

  # Check Python3
  if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found${NC}"; exit 1
  fi

  # Check Mininet
  if ! command -v mn &>/dev/null; then
    echo -e "${YELLOW}[SETUP] Installing Mininet...${NC}"
    apt-get update -q
    apt-get install -y mininet
  fi

  # Check Ryu
  if ! python3 -c "import ryu" &>/dev/null; then
    echo -e "${YELLOW}[SETUP] Installing Ryu...${NC}"
    pip3 install ryu --quiet
  fi

  # Check OVS
  if ! command -v ovs-vsctl &>/dev/null; then
    echo -e "${YELLOW}[SETUP] Installing Open vSwitch...${NC}"
    apt-get install -y openvswitch-switch
  fi

  # Check iperf3
  if ! command -v iperf3 &>/dev/null; then
    echo -e "${YELLOW}[SETUP] Installing iperf3...${NC}"
    apt-get install -y iperf3
  fi

  echo -e "${GREEN}[SETUP] All dependencies satisfied.${NC}"
}

cleanup() {
  echo -e "${YELLOW}[CLEANUP] Cleaning up previous Mininet state...${NC}"
  mn -c 2>/dev/null || true
  pkill -f ryu-manager 2>/dev/null || true
  pkill -f access_control_controller 2>/dev/null || true
  sleep 1
}

start_controller() {
  echo -e "${GREEN}[CTRL] Starting Ryu controller...${NC}"
  echo -e "       Controller log: /tmp/ryu_controller.log"
  ryu-manager \
    --observe-links \
    --ofp-tcp-listen-port 6633 \
    controller/access_control_controller.py \
    > /tmp/ryu_controller.log 2>&1 &
  CTRL_PID=$!
  echo -e "${GREEN}[CTRL] Controller PID: $CTRL_PID${NC}"
  sleep 2

  # Verify controller started
  if ! kill -0 $CTRL_PID 2>/dev/null; then
    echo -e "${RED}[ERROR] Controller failed to start. Check /tmp/ryu_controller.log${NC}"
    cat /tmp/ryu_controller.log
    exit 1
  fi
  echo -e "${GREEN}[CTRL] Controller running on port 6633${NC}"
}

start_topology_demo() {
  echo -e "${GREEN}[TOPO] Starting Mininet topology (interactive mode)...${NC}"
  echo ""
  echo -e "${CYAN}  Useful Mininet CLI commands:${NC}"
  echo -e "  ${YELLOW}pingall${NC}              → Test all-pairs connectivity"
  echo -e "  ${YELLOW}h1 ping h2${NC}           → Authorized ping (should work)"
  echo -e "  ${YELLOW}h4 ping h1${NC}           → Unauthorized ping (should FAIL)"
  echo -e "  ${YELLOW}h1 iperf3 -s &${NC}       → Start iperf server on h1"
  echo -e "  ${YELLOW}h2 iperf3 -c 10.0.0.1${NC} → Test throughput h2→h1"
  echo -e "  ${YELLOW}dump${NC}                 → Show node info"
  echo -e "  ${YELLOW}sh ovs-ofctl -O OpenFlow13 dump-flows s1${NC} → View flow table"
  echo ""
  python3 topology/access_control_topo.py
}

start_topology_test() {
  echo -e "${GREEN}[TOPO] Starting Mininet topology (automated test mode)...${NC}"
  python3 topology/access_control_topo.py --test
}

monitor_logs() {
  echo -e "\n${CYAN}[INFO] To monitor controller logs in real-time:${NC}"
  echo -e "       tail -f /tmp/ryu_controller.log"
  echo ""
  echo -e "${CYAN}[INFO] To view flow tables:${NC}"
  echo -e "       sudo ovs-ofctl -O OpenFlow13 dump-flows s1"
  echo ""
}

# ── MAIN ─────────────────────────────────────
banner
check_root
install_deps
cleanup

case "$MODE" in
  controller)
    start_controller
    echo -e "${GREEN}[INFO] Controller running. Start topology separately:${NC}"
    echo -e "       sudo python3 topology/access_control_topo.py"
    monitor_logs
    wait
    ;;
  test)
    start_controller
    monitor_logs
    start_topology_test
    ;;
  demo|*)
    start_controller
    monitor_logs
    start_topology_demo
    ;;
esac
