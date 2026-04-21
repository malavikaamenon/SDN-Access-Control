
from pox.core import core
from pox.lib.util import dpid_to_str
from pox.lib.addresses import EthAddr
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
import time
import logging

log = core.getLogger()


WHITELIST = {
    EthAddr('00:00:00:00:00:01'),   # h1 - Authorized
    EthAddr('00:00:00:00:00:02'),   # h2 - Authorized
    EthAddr('00:00:00:00:00:03'),   # h3 - Authorized
    # 00:00:00:00:00:04 → h4 UNAUTHORIZED
    # 00:00:00:00:00:05 → h5 UNAUTHORIZED
}

# Flow rule priorities
PRIORITY_DENY       = 100   
PRIORITY_ALLOW      = 10   
PRIORITY_TABLE_MISS = 0    

# Timeouts
ALLOW_IDLE_TIMEOUT = 30   
ALLOW_HARD_TIMEOUT = 0    
DENY_IDLE_TIMEOUT  = 0    
DENY_HARD_TIMEOUT  = 0


class AccessControlSwitch(object):
    """
    Per-switch access control instance.
    Each switch that connects gets its own AccessControlSwitch object.
    """

    def __init__(self, connection):
        self.connection = connection
        self.dpid = connection.dpid

        # MAC-to-port learning table for this switch
        self.mac_to_port = {}

        # Statistics
        self.stats = {
            'allowed': 0,
            'denied':  0,
            'total':   0,
        }

        # Listen for packet_in events on this connection
        connection.addListeners(self)

        # Install table-miss entry: send unmatched packets to controller
        self._install_table_miss()

        log.info("Switch connected: %s", dpid_to_str(self.dpid))
        log.info("Whitelist: %s", [str(m) for m in WHITELIST])

    def _install_table_miss(self):
       
        msg = of.ofp_flow_mod()
        msg.priority = PRIORITY_TABLE_MISS
        msg.match = of.ofp_match()   # Match everything
        msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        self.connection.send(msg)
        log.info("[SWITCH] Table-miss entry installed on %s",
                 dpid_to_str(self.dpid))

    def _add_flow(self, match, actions, priority,
                  idle_timeout=0, hard_timeout=0):
        
        msg = of.ofp_flow_mod()
        msg.match        = match
        msg.priority     = priority
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        msg.actions      = actions   # Empty list = DROP
        self.connection.send(msg)

    def _packet_out(self, event, out_port):
        
        msg = of.ofp_packet_out()
        msg.data        = event.ofp
        msg.in_port     = event.port
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    def _drop_packet(self, event):
      
        msg = of.ofp_packet_out()
        msg.data    = event.ofp
        msg.in_port = event.port
        # No actions = drop
        self.connection.send(msg)

    def _handle_PacketIn(self, event):
      
        packet  = event.parsed
        in_port = event.port

        if not packet.parsed:
            log.warning("Unparsed packet — ignoring")
            return

        src_mac = packet.src
        dst_mac = packet.dst

        self.stats['total'] += 1

        # Skip LLDP and IPv6 multicast — not relevant to our policy
        if packet.type == packet.LLDP_TYPE:
            return
        if str(src_mac).startswith('33:33'):
            return

        log.info("[PKT-IN] DPID=%s  src=%s  dst=%s  port=%d",
                 dpid_to_str(self.dpid), src_mac, dst_mac, in_port)

        # ── ACCESS CONTROL CHECK ────────────────────────────────
        src_authorized = src_mac in WHITELIST
        # Allow broadcasts and multicasts through (ARP needs this)
        dst_authorized = (dst_mac in WHITELIST or
                          dst_mac == EthAddr('ff:ff:ff:ff:ff:ff') or
                          str(dst_mac).startswith('33:33') or
                          str(dst_mac).startswith('01:00:5e'))

        if not src_authorized:
            self._handle_unauthorized(event, src_mac, dst_mac,
                                      reason="src not in whitelist")
            return

        if not dst_authorized:
            self._handle_unauthorized(event, src_mac, dst_mac,
                                      reason="dst not in whitelist")
            return

        # ── BOTH AUTHORIZED — learning switch logic ─────────────
        # Learn the source MAC → port mapping
        self.mac_to_port[src_mac] = in_port

        # Determine output port
        if dst_mac in self.mac_to_port:
            out_port = self.mac_to_port[dst_mac]
        else:
            out_port = of.OFPP_FLOOD   # Unknown dst → flood

        # Install proactive allow rule for known unicast destinations
        if out_port != of.OFPP_FLOOD:
            match = of.ofp_match()
            match.in_port  = in_port
            match.dl_src   = src_mac
            match.dl_dst   = dst_mac

            actions = [of.ofp_action_output(port=out_port)]

            self._add_flow(match, actions,
                           priority=PRIORITY_ALLOW,
                           idle_timeout=ALLOW_IDLE_TIMEOUT,
                           hard_timeout=ALLOW_HARD_TIMEOUT)

            self.stats['allowed'] += 1
            log.info("[ALLOW] Flow installed: %s → %s  port %d → %d",
                     src_mac, dst_mac, in_port, out_port)

        # Forward the current packet immediately
        self._packet_out(event, out_port)

    def _handle_unauthorized(self, event, src_mac, dst_mac, reason):
        """
        Installs a DROP rule for the unauthorized source MAC
        and drops the current packet.
        """
        # Install deny rule: match on in_port + src_mac, no actions = DROP
        match = of.ofp_match()
        match.in_port = event.port
        match.dl_src  = src_mac

        self._add_flow(match, actions=[],
                       priority=PRIORITY_DENY,
                       idle_timeout=DENY_IDLE_TIMEOUT,
                       hard_timeout=DENY_HARD_TIMEOUT)

        self.stats['denied'] += 1
        log.warning("[DENY]  Unauthorized: src=%s  dst=%s  reason=%s",
                    src_mac, dst_mac, reason)

        # Drop the current packet
        self._drop_packet(event)


class AccessControlController(EventMixin):
   

    def __init__(self):
        self._listen_to_connects()
        log.info("=" * 55)
        log.info("  SDN Access Control Controller Started (POX)")
        log.info("  Authorized hosts: %s",
                 [str(m) for m in WHITELIST])
        log.info("=" * 55)

    def _listen_to_connects(self):
        core.openflow.addListenerByName(
            "ConnectionUp", self._handle_ConnectionUp)

    def _handle_ConnectionUp(self, event):
        """Called when a switch connects to the controller."""
        log.info("[CTRL] New switch connected: %s",
                 dpid_to_str(event.dpid))
        AccessControlSwitch(event.connection)


def launch():
    
    core.registerNew(AccessControlController)
