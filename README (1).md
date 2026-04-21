# SDN-Based Access Control System

[![OpenFlow](https://img.shields.io/badge/OpenFlow-1.0-blue)](https://opennetworking.org/)
[![POX](https://img.shields.io/badge/Controller-POX-orange)](https://github.com/noxrepo/pox)
[![Mininet](https://img.shields.io/badge/Emulator-Mininet-green)](http://mininet.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow)](https://python.org/)
[![Ubuntu](https://img.shields.io/badge/OS-Ubuntu%2022.04-purple)](https://ubuntu.com/)

---

## Problem Statement

Traditional networks rely on distributed, per-device ACLs that are difficult
to manage consistently. This project implements a **centralized, policy-driven
access control system** using Software-Defined Networking (SDN).

A POX OpenFlow controller enforces a whitelist of authorized MAC addresses
across all switches. Only permitted hosts can communicate. All others are
blocked at the switch level using OpenFlow flow rules.

**Key objectives:**
- Maintain a whitelist of authorized host MAC addresses
- Install explicit `allow` and `deny` OpenFlow rules at the switch
- Block all unauthorized access attempts proactively
- Verify behavior through functional and regression testing
- Demonstrate centralized policy with distributed enforcement

---

## Architecture

```
                    ┌──────────────────────────────────┐
                    │         POX Controller           │
                    │   access_control_controller.py   │
                    │                                  │
                    │   WHITELIST:                     │
                    │     00:00:00:00:00:01  h1 ✓      │
                    │     00:00:00:00:00:02  h2 ✓      │
                    │     00:00:00:00:00:03  h3 ✓      │
                    │     (h4, h5 absent → blocked)    │
                    └──────────────┬───────────────────┘
                                   │ OpenFlow 1.0
                                   │ TCP port 6633
                    ┌──────────────▼───────────────────┐
                    │          Switch s1               │
                    │     OVS · OpenFlow 1.0           │
                    └───┬──────┬──────┬─────┬──────────┘
                        │      │      │     │     │
                       h1     h2     h3    h4    h5
                    (auth)  (auth) (auth) (BLOCK)(BLOCK)
                   10.0.0.1  .2     .3     .4     .5
```

### Flow Rule Design

| Priority | Match                          | Action       | Purpose                    |
|----------|--------------------------------|--------------|----------------------------|
| 100      | in_port + src_mac (unauth)     | DROP         | Block unauthorized host    |
| 10       | in_port + src_mac + dst_mac    | output:N     | Forward authorized flow    |
| 0        | any                            | CONTROLLER   | Table-miss → packet_in     |

**Priority 100 > 10 > 0** — deny rules are always evaluated before allow rules.

---

## Project Structure

```
sdn-access-control/
├── controller/
│   └── access_control_controller.py   # POX OpenFlow controller (whitelist logic)
├── topology/
│   └── access_control_topo.py         # Mininet star topology (5 hosts, 1 switch)
├── tests/
│   └── run_tests.py                   # Functional + regression test suite
└── README.md
```

---

## Prerequisites

| Tool         | Version  | Purpose                        |
|--------------|----------|-------------------------------|
| Ubuntu       | 22.04    | Operating system               |
| Python       | 3.10     | Runtime                        |
| Mininet      | 2.3+     | Network emulation              |
| Open vSwitch | 2.17+    | Virtual switch                 |
| POX          | 0.7.0    | SDN controller                 |
| iperf3       | 3.x      | Throughput testing             |

---

## Setup & Installation

### Step 1 — Install system dependencies
```bash
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch iperf3 git
```

### Step 2 — Install POX
```bash
cd ~
git clone https://github.com/noxrepo/pox.git
```

### Step 3 — Clone this project
```bash
cd ~
git clone https://github.com/<your-username>/sdn-access-control.git
```

### Step 4 — Copy controller into POX
```bash
cp ~/sdn-access-control/controller/access_control_controller.py \
   ~/pox/pox/misc/access_control_controller.py
```

### Step 5 — Verify POX works
```bash
cd ~/pox
python3 pox.py --version
```
Expected output:
```
POX 0.7.0 (gar) / Copyright 2011-2020 James McCauley, et al.
```

---

## Running the Project

You need **two terminals** open at the same time.

---

### Terminal 1 — Start the POX Controller

```bash
cd ~/pox
python3 pox.py misc.access_control_controller
```

**Expected output:**
```
POX 0.7.0 (gar) / Copyright 2011-2020 James McCauley, et al.
INFO:misc.access_control_controller:=======================================================
INFO:misc.access_control_controller:  SDN Access Control Controller Started (POX)
INFO:misc.access_control_controller:  Whitelist: ['00:00:00:00:00:01', '00:00:00:00:00:02', '00:00:00:00:00:03']
INFO:misc.access_control_controller:=======================================================
INFO:core:POX 0.7.0 (gar) is up.
```

Leave this running. Wait for `POX is up` before starting Terminal 2.

---

### Terminal 2 — Start Mininet Topology

```bash
sudo mn -c
cd ~/sdn-access-control
sudo python3 topology/access_control_topo.py
```

**Expected output:**
```
============================================================
  SDN Access Control Topology
  Controller: 127.0.0.1:6633
============================================================
[TOPO] Adding authorized hosts h1, h2, h3...
[TOPO] Adding unauthorized hosts h4, h5...
[NET] Starting network...
*** Starting CLI:
mininet>
```

**At this point Terminal 1 (POX) will show:**
```
INFO:openflow.of_01:[00-00-00-00-00-01 2] connected
INFO:misc.access_control_controller:[CTRL] Switch connected: 00-00-00-00-00-01
INFO:misc.access_control_controller:[SWITCH] Table-miss installed on 00-00-00-00-00-01
```

---

## Running the Tests

All test commands are typed at the `mininet>` prompt in Terminal 2.

---

### Verify topology loaded

```bash
mininet> nodes
mininet> dump
```

Expected:
```
available nodes are:
c0 h1 h2 h3 h4 h5 s1

<Host h1: h1-eth0:10.0.0.1 pid=XXXX>
<Host h2: h2-eth0:10.0.0.2 pid=XXXX>
<Host h3: h3-eth0:10.0.0.3 pid=XXXX>
<Host h4: h4-eth0:10.0.0.4 pid=XXXX>
<Host h5: h5-eth0:10.0.0.5 pid=XXXX>
<OVSSwitch s1: lo:127.0.0.1 ...>
<RemoteController c0: 127.0.0.1:6633 ...>
```

---

### SCENARIO 1 — Authorized hosts (expect 0% packet loss)

```bash
mininet> h1 ping -c 4 h2
mininet> h2 ping -c 4 h3
mininet> h1 ping -c 4 h3
```

**Expected output for each:**
```
64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=132 ms
64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=8.21 ms
64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=6.53 ms
64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=6.27 ms
4 packets transmitted, 4 received, 0% packet loss
```

**POX Terminal 1 will show:**
```
[PKT-IN] src=00:00:00:00:00:01  dst=00:00:00:00:00:02  port=1
[ALLOW] 00:00:00:00:00:01 -> 00:00:00:00:00:02  port 1 -> 2
```

---

### SCENARIO 2 — Unauthorized hosts (expect 100% packet loss)

```bash
mininet> h4 ping -c 4 h1
mininet> h5 ping -c 4 h2
mininet> h4 ping -c 4 h5
```

**Expected output for each:**
```
From 10.0.0.4 icmp_seq=1 Destination Host Unreachable
From 10.0.0.4 icmp_seq=2 Destination Host Unreachable
From 10.0.0.4 icmp_seq=3 Destination Host Unreachable
From 10.0.0.4 icmp_seq=4 Destination Host Unreachable
4 packets transmitted, 0 received, 100% packet loss
```

**POX Terminal 1 will show:**
```
[PKT-IN] src=00:00:00:00:00:04  dst=...  port=4
[DENY] src=00:00:00:00:00:04 dst=... reason=src not in whitelist
```

---

### SCENARIO 3 — iperf3 throughput test

```bash
# Start server on h1
mininet> h1 iperf3 -s &

# Run client from authorized h2 (should get throughput)
mininet> h2 iperf3 -c 10.0.0.1 -t 5

# Run client from unauthorized h4 (should fail)
mininet> h4 iperf3 -c 10.0.0.1 -t 5

# Kill server
mininet> h1 kill %iperf3
```

**Expected h2 output (authorized):**
```
[ ID] Interval        Transfer     Bitrate
[  5] 0.00-5.00 sec   22.2 MBytes  37.2 Mbits/sec   sender
```

**Expected h4 output (blocked):**
```
iperf3: error - unable to send control message: Bad file descriptor
```

---

### SCENARIO 4 — View flow table (open Terminal 3)

```bash
sudo ovs-ofctl dump-flows s1
```

**Expected output:**
```
cookie=0x0, priority=100, in_port="s1-eth4", dl_src=00:00:00:00:00:04
  actions=drop

cookie=0x0, priority=100, in_port="s1-eth5", dl_src=00:00:00:00:00:05
  actions=drop

cookie=0x0, duration=22s, idle_timeout=30, priority=10,
  in_port="s1-eth1", dl_src=00:00:00:00:00:01, dl_dst=00:00:00:00:00:02
  actions=output:"s1-eth2"

cookie=0x0, duration=22s, idle_timeout=30, priority=10,
  in_port="s1-eth2", dl_src=00:00:00:00:00:02, dl_dst=00:00:00:00:00:01
  actions=output:"s1-eth1"

cookie=0x0, priority=0
  actions=CONTROLLER:65535
```

This shows all three rule types working:
- `priority=100 actions=drop` — h4 and h5 permanently denied
- `priority=10 actions=output:N` — authorized flows forwarded
- `priority=0 actions=CONTROLLER` — table-miss sends unknown to controller

---

### REGRESSION TEST — Policy consistency

```bash
# Run unauthorized ping twice — both must be blocked
mininet> h4 ping -c 3 h1
mininet> h4 ping -c 3 h1

# Authorized host must still work after deny rules installed
mininet> h1 ping -c 3 h2
```

**Expected:**
```
h4 ping h1 (first):   100% packet loss   ✓
h4 ping h1 (second):  100% packet loss   ✓  (deny rule persists)
h1 ping h2:           0% packet loss     ✓  (authorized unaffected)
```

---

### Clean exit

```bash
mininet> exit
sudo mn -c
```

Press `Ctrl+C` in Terminal 1 to stop POX.

---

## Proof of Execution

### Flow Table (actual output)
```
cookie=0x0, duration=489s, priority=100,
  in_port="s1-eth4", dl_src=00:00:00:00:00:04  actions=drop

cookie=0x0, duration=489s, priority=100,
  in_port="s1-eth5", dl_src=00:00:00:00:00:05  actions=drop

cookie=0x0, duration=22s, idle_timeout=30, priority=10,
  in_port="s1-eth1", dl_src=00:00:00:00:00:01,
  dl_dst=00:00:00:00:00:02  actions=output:"s1-eth2"

cookie=0x0, duration=22s, idle_timeout=30, priority=10,
  in_port="s1-eth2", dl_src=00:00:00:00:00:02,
  dl_dst=00:00:00:00:00:01  actions=output:"s1-eth1"

cookie=0x0, duration=489s, priority=0  actions=CONTROLLER:65535
```

### Ping Results (actual output)

**Authorized — h1 → h2:**
```
4 packets transmitted, 4 received, 0% packet loss
rtt min/avg/max/mdev = 6.268/38.324/132.293/54.257 ms
```

**Unauthorized — h4 → h1:**
```
4 packets transmitted, 0 received, +4 errors, 100% packet loss
```

### iperf3 Results (actual output)

**Authorized — h2 → h1:**
```
[ ID] Interval        Transfer    Bitrate       Retr
[  5] 0.00-5.00 sec   22.2 MBytes 37.2 Mbits/sec  0   sender
[  5] 0.00-5.41 sec   18.9 MBytes 29.3 Mbits/sec      receiver
```

**Unauthorized — h4 → h1:**
```
iperf3: error - unable to send control message: Bad file descriptor
```

### POX Controller Log (actual output)
```
[DENY]  src=00:00:00:00:00:04  reason=src not in whitelist
[DENY]  src=00:00:00:00:00:05  reason=src not in whitelist
[ALLOW] 00:00:00:00:00:01 -> 00:00:00:00:00:02  port 1 -> 2
[ALLOW] 00:00:00:00:00:02 -> 00:00:00:00:00:01  port 2 -> 1
[ALLOW] 00:00:00:00:00:03 -> 00:00:00:00:00:02  port 3 -> 2
[ALLOW] 00:00:00:00:00:01 -> 00:00:00:00:00:03  port 1 -> 3
```

---

## Performance Metrics

| Metric                        | Value              |
|-------------------------------|--------------------|
| Authorized ping RTT (avg)     | ~38 ms (OVS/venv)  |
| Unauthorized ping loss        | 100%               |
| iperf3 throughput (authorized)| 37.2 Mbits/sec     |
| iperf3 throughput (blocked)   | 0 (connection error)|
| Deny rule install latency     | < 5 ms (first pkt) |
| Allow rule install latency    | < 5 ms (first pkt) |

---

## Whitelist Configuration

To authorize additional hosts, edit the WHITELIST in the controller:

```python
# controller/access_control_controller.py

WHITELIST = {
    EthAddr('00:00:00:00:00:01'),   # h1 - Authorized
    EthAddr('00:00:00:00:00:02'),   # h2 - Authorized
    EthAddr('00:00:00:00:00:03'),   # h3 - Authorized
    EthAddr('00:00:00:00:00:04'),   # uncomment to authorize h4
}
```

Restart the POX controller after any change.

---

## SDN Concepts Demonstrated

| Concept                  | Implementation                                          |
|--------------------------|---------------------------------------------------------|
| Centralized control      | Single POX controller manages policy for all switches   |
| packet_in handling       | `_handle_PacketIn` processes every new unknown flow     |
| Match + action design    | ofp_match on in_port, dl_src, dl_dst; action = output or drop |
| Flow rule installation   | ofp_flow_mod with priority, idle/hard timeout           |
| Reactive forwarding      | Unknown dst → flood; known dst → install proactive rule |
| Policy enforcement       | Whitelist checked on every packet_in before forwarding  |
| Table-miss entry         | Default priority-0 rule sends unmatched pkts to controller |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ryu-manager: command not found` | Use POX instead — see setup steps above |
| Switch not connecting to POX | Make sure POX is running before starting Mininet |
| `ovs-ofctl: Permission denied` | Use `sudo ovs-ofctl dump-flows s1` |
| All pings failing including authorized | Run `sudo mn -c`, restart POX, restart topology |
| `sch_htb: quantum of class 50001 is big` | Harmless warning from TCLink, ignore it |
| POX Python 3.10 warning | Harmless, POX works fine on Python 3.10 |

---

## References

1. OpenFlow Switch Specification v1.0 — Open Networking Foundation
   https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf

2. POX Controller Documentation and Source
   https://github.com/noxrepo/pox

3. Mininet Walkthrough
   http://mininet.org/walkthrough/

4. B. Lantz, B. Heller, N. McKeown, "A Network in a Laptop: Rapid Prototyping
   for Software-Defined Networks," HotNets-IX, 2010.

5. N. McKeown et al., "OpenFlow: Enabling Innovation in Campus Networks,"
   ACM SIGCOMM Computer Communication Review, 2008.

6. POX Wiki — Writing a POX Component
   https://noxrepo.github.io/pox-doc/html/
