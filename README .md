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



### Flow Rule Design

| Priority | Match                          | Action       | Purpose                    |
|----------|--------------------------------|--------------|----------------------------|
| 100      | in_port + src_mac (unauth)     | DROP         | Block unauthorized host    |
| 10       | in_port + src_mac + dst_mac    | output:N     | Forward authorized flow    |
| 0        | any                            | CONTROLLER   | Table-miss → packet_in     |

**Priority 100 > 10 > 0** — deny rules are always evaluated before allow rules.

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

### Step 4 — Copy controller into POX
```bash
cp ~/sdn-access-control/controller/access_control_controller.py \
   ~/pox/pox/misc/access_control_controller.py
```


---

## Running the Project


### Terminal 1 — Start the POX Controller

```bash
cd ~/pox
python3 pox.py misc.access_control_controller
```

<img width="1472" height="866" alt="image" src="https://github.com/user-attachments/assets/55d3ab1e-d661-4af7-afa8-aee6c281a355" />


---

### Terminal 2 — Start Mininet Topology

```bash
sudo mn -c
cd ~/sdn-access-control
sudo python3 topology/access_control_topo.py
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
<img width="1464" height="754" alt="image" src="https://github.com/user-attachments/assets/5ff47ec2-7054-4f6c-adbc-68c4e7a1e75d" />


---

### SCENARIO 1 — Authorized hosts (expect 0% packet loss)

```bash
mininet> h1 ping -c 4 h2
mininet> h2 ping -c 4 h3
mininet> h1 ping -c 4 h3
```

<img width="1436" height="860" alt="image" src="https://github.com/user-attachments/assets/fb8b73b6-9f4f-4680-aab2-0122d23a1bb8" />



---

### SCENARIO 2 — Unauthorized hosts (expect 100% packet loss)

```bash
mininet> h4 ping -c 4 h1
mininet> h5 ping -c 4 h2
mininet> h4 ping -c 4 h5
```

<img width="1442" height="488" alt="image" src="https://github.com/user-attachments/assets/e46e2ce1-fbc9-4527-b079-ec382a93c36f" />



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

<img width="1454" height="718" alt="image" src="https://github.com/user-attachments/assets/7b1d63b6-906e-4e7e-af0f-464e798c50c4" />

<img width="1420" height="1014" alt="image" src="https://github.com/user-attachments/assets/18efa210-ca46-42d2-8adb-e2ec1bfeb899" />



---

### SCENARIO 4 — View flow table (open Terminal 3)

```bash
sudo ovs-ofctl dump-flows s1
```

<img width="1434" height="298" alt="image" src="https://github.com/user-attachments/assets/59158ad7-9279-4468-8b09-2bee8bc3ca99" />


---

### REGRESSION TEST — Policy consistency

```bash
# Run unauthorized ping twice — both must be blocked
mininet> h4 ping -c 3 h1
mininet> h4 ping -c 3 h1

# Authorized host must still work after deny rules installed
mininet> h1 ping -c 3 h2
```

<img width="1328" height="616" alt="image" src="https://github.com/user-attachments/assets/fb0db4c1-ddcb-46b6-8f28-83eb181ba8ed" />

<img width="1458" height="726" alt="image" src="https://github.com/user-attachments/assets/9367aece-639d-471b-9ce8-40d948c30dfc" />


---

### Clean exit

```bash
mininet> exit
sudo mn -c
```

