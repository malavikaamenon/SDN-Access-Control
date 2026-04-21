#!/usr/bin/env python3
"""
Mininet Topology for SDN Access Control System
================================================
Creates a star topology with one OpenFlow switch and 5 hosts:
  - h1, h2, h3 → AUTHORIZED (in whitelist)
  - h4         → UNAUTHORIZED (not in whitelist)
  - h5         → UNAUTHORIZED (not in whitelist)

Topology Diagram:
                    ┌──────────────────────┐
                    │    Ryu Controller    │
                    │  (OpenFlow 1.3)      │
                    │  127.0.0.1:6633      │
                    └──────────┬───────────┘
                               │ OpenFlow
                    ┌──────────▼───────────┐
                    │      Switch s1       │
                    │   (OVS OpenFlow13)   │
                    └──┬──┬──┬──┬──┬───────┘
                       │  │  │  │  │
                  ┌────┘  │  │  │  └────┐
                  │   ┌───┘  │  └───┐   │
                 h1  h2     h3     h4  h5
               (auth)(auth)(auth)(unauth)(unauth)

IP Assignments:
  h1: 10.0.0.1/24  MAC: 00:00:00:00:00:01
  h2: 10.0.0.2/24  MAC: 00:00:00:00:00:02
  h3: 10.0.0.3/24  MAC: 00:00:00:00:00:03
  h4: 10.0.0.4/24  MAC: 00:00:00:00:00:04  ← BLOCKED
  h5: 10.0.0.5/24  MAC: 00:00:00:00:00:05  ← BLOCKED

Usage:
    sudo python3 topology/access_control_topo.py
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time
import sys


def create_topology():
    """
    Builds and returns the Mininet network with the access control topology.
    """
    info("=" * 60 + "\n")
    info("  SDN Access Control Topology\n")
    info("  Controller: 127.0.0.1:6633\n")
    info("=" * 60 + "\n")

    # Create network with remote Ryu controller and OVS switches
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=False  # We set MACs manually for predictability
    )

    # ── Add remote Ryu controller ────────────────
    info("[TOPO] Adding Ryu controller...\n")
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6633
    )

    # ── Add OpenFlow 1.3 switch ──────────────────
    info("[TOPO] Adding switch s1 (OpenFlow13)...\n")
    s1 = net.addSwitch('s1', protocols='OpenFlow10')

    # ── Add AUTHORIZED hosts (in whitelist) ──────
    info("[TOPO] Adding authorized hosts h1, h2, h3...\n")
    h1 = net.addHost('h1',
                     ip='10.0.0.1/24',
                     mac='00:00:00:00:00:01')
    h2 = net.addHost('h2',
                     ip='10.0.0.2/24',
                     mac='00:00:00:00:00:02')
    h3 = net.addHost('h3',
                     ip='10.0.0.3/24',
                     mac='00:00:00:00:00:03')

    # ── Add UNAUTHORIZED hosts (not in whitelist) ─
    info("[TOPO] Adding unauthorized hosts h4, h5...\n")
    h4 = net.addHost('h4',
                     ip='10.0.0.4/24',
                     mac='00:00:00:00:00:04')  # Will be blocked
    h5 = net.addHost('h5',
                     ip='10.0.0.5/24',
                     mac='00:00:00:00:00:05')  # Will be blocked

    # ── Add links (100 Mbps, 1ms delay) ──────────
    info("[TOPO] Adding links...\n")
    link_opts = dict(bw=100, delay='1ms', loss=0)
    net.addLink(h1, s1, **link_opts)
    net.addLink(h2, s1, **link_opts)
    net.addLink(h3, s1, **link_opts)
    net.addLink(h4, s1, **link_opts)
    net.addLink(h5, s1, **link_opts)

    return net


def run_automated_tests(net):
    """
    Runs a series of automated connectivity tests demonstrating
    the access control behavior.
    """
    h1 = net.get('h1')
    h2 = net.get('h2')
    h3 = net.get('h3')
    h4 = net.get('h4')
    h5 = net.get('h5')

    info("\n" + "=" * 60 + "\n")
    info("  AUTOMATED TEST SUITE\n")
    info("=" * 60 + "\n")

    # Allow controller to install default rules
    info("[TEST] Waiting 3s for controller to initialize...\n")
    time.sleep(3)

    results = []

    # ── SCENARIO 1: Authorized host communication ─
    info("\n[SCENARIO 1] Authorized hosts communicating\n")
    info("-" * 40 + "\n")

    tests_allowed = [
        (h1, h2, "h1 → h2 (both authorized)"),
        (h2, h3, "h2 → h3 (both authorized)"),
        (h1, h3, "h1 → h3 (both authorized)"),
    ]

    for src, dst, label in tests_allowed:
        result = src.cmd(f'ping -c 3 -W 2 {dst.IP()}')
        loss_line = [l for l in result.split('\n') if 'packet loss' in l]
        loss = loss_line[0] if loss_line else "unknown"
        passed = '0% packet loss' in result
        status = "✓ PASS" if passed else "✗ FAIL"
        info(f"  [{status}] {label}\n")
        info(f"          {loss}\n")
        results.append((label, passed))
        time.sleep(1)

    # ── SCENARIO 2: Unauthorized host blocked ─────
    info("\n[SCENARIO 2] Unauthorized hosts blocked\n")
    info("-" * 40 + "\n")

    tests_blocked = [
        (h4, h1, "h4 → h1 (h4 unauthorized, SHOULD BE BLOCKED)"),
        (h4, h2, "h4 → h2 (h4 unauthorized, SHOULD BE BLOCKED)"),
        (h5, h1, "h5 → h1 (h5 unauthorized, SHOULD BE BLOCKED)"),
        (h5, h3, "h5 → h3 (h5 unauthorized, SHOULD BE BLOCKED)"),
    ]

    for src, dst, label in tests_blocked:
        result = src.cmd(f'ping -c 3 -W 2 {dst.IP()}')
        # Blocked = 100% packet loss
        passed = '100% packet loss' in result or '3 packets transmitted, 0 received' in result
        status = "✓ PASS" if passed else "✗ FAIL"
        info(f"  [{status}] {label}\n")
        results.append((label, passed))
        time.sleep(1)

    # ── SCENARIO 3: Unauthorized→Unauthorized ─────
    info("\n[SCENARIO 3] Between unauthorized hosts\n")
    info("-" * 40 + "\n")

    result = h4.cmd(f'ping -c 3 -W 2 {h5.IP()}')
    passed = '100% packet loss' in result or '3 packets transmitted, 0 received' in result
    label = "h4 → h5 (both unauthorized, SHOULD BE BLOCKED)"
    status = "✓ PASS" if passed else "✗ FAIL"
    info(f"  [{status}] {label}\n")
    results.append((label, passed))

    # ── SUMMARY ───────────────────────────────────
    info("\n" + "=" * 60 + "\n")
    info("  TEST SUMMARY\n")
    info("=" * 60 + "\n")
    passed_count = sum(1 for _, p in results if p)
    info(f"  Results: {passed_count}/{len(results)} tests passed\n")
    for label, passed in results:
        icon = "✓" if passed else "✗"
        info(f"  [{icon}] {label}\n")
    info("=" * 60 + "\n")

    return results


def main():
    setLogLevel('info')

    net = create_topology()

    info("[NET] Starting network...\n")
    net.start()

    # Configure OVS to use OpenFlow 1.3
    info("[NET] Configuring OVS for OpenFlow 1.3...\n")
    net.get('s1').cmd('ovs-vsctl set bridge s1 protocols=OpenFlow10')

    if '--test' in sys.argv:
        # Automated test mode
        run_automated_tests(net)
        net.stop()
    else:
        # Interactive mode
        info("\n[NET] Network ready. Type 'help' for Mininet CLI commands.\n")
        info("[NET] Run 'python3 tests/run_tests.py' in another terminal "
             "for automated tests.\n\n")
        CLI(net)
        net.stop()


if __name__ == '__main__':
    main()
