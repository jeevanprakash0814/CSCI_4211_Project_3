from pox.core import core
import pox.openflow.libopenflow_01 as of


# Even a simple usage of the logger is much nicer than print!
log = core.getLogger()


# !!!!! PROJ3 Define your data structures here
switches = {} # switch ID to switch table


# Handle messages the switch has sent us because it has no
# matching rule.

def _handle_PacketIn (event):


  # get the port the packet came in on for the switch contacting the controller
  packetInPort = event.port

  # use POX to parse the packet
  packet = event.parsed

  # get src and dst mac addresses
  src_mac = str(packet.src)
  dst_mac = str(packet.dst)

  # get switch ID
  switchID = str(event.connection.dpid) + str(event.connection.ID)
  
  log.info('Packet has arrived: SRCMAC:{} DSTMAC:{} from switch:{} in-port:{}'.format(src_mac, dst_mac, switchID, packetInPort))

  # !!!!! PROJ3 Your logic goes here
  # method for flooding the packet into the network
  def flood ():
    '''
    Method for flooding the packet into the network
    '''
    msg = of.ofp_packet_out() # create an output message
    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD)) # add a flooding action to this message
    msg.data = event.ofp # set the message payload
    msg.in_port = packetInPort # set the in port as incoming port of the packet
    event.connection.send(msg) # send the message to the switch for flooding

  def drop (duration = None):
    '''
    Method for dropping a packet and concurrent packets that are the same
    '''
    if duration is not None:
      if not isinstance(duration, tuple):
        duration = (duration,duration)
      
      msg = of.ofp_flow_mod() # create a new flow message
      msg.match = of.ofp_match.from_packet(packet) # if it is from this specific packet, drop it
      msg.idle_timeout = duration[0]
      msg.hard_timeout = duration[1]
      msg.buffer_id = event.ofp.buffer_id
      event.connection.send(msg) # send the drop flow to the switch
    elif event.ofp.buffer_id is not None:
      msg = of.ofp_packet_out()
      msg.buffer_id = event.ofp.buffer_id
      msg.in_port = event.port
      event.connection.send(msg)

  # main logic 
  if not switches.has_key(switchID): # if the switch is not in the switch dictionary
    switches[switchID] = {} # add a switch table for the new switch
  switches[switchID][src_mac] = packetInPort # add the source mac address to the current switches, switch table

  # if the packet is multicast (the destination mac address is set to #FF-FF-FF-FF), then flood
  # or if the destination mac address is not found in the switch's switch table, then flood
  if not packet.dst.is_multicast or switches[switchID].has_key(dst_mac):
    flood() # initiate flooding
  elif packetInPort is switches[switchID][dst_mac]: # if the in port is the same as out port, then drop the packet and any similar subsequent packets
    drop(10)
    return
  else: # if the destination port is found, construct a flow message and send it to the switch
    msg = of.ofp_flow_mod() # construct a flow message
    msg.match = of.ofp_match.from_packet(packet, packetInPort) # make sure the packet and the source port matches
    msg.idle_timeout = 10
    msg.hard_timeout = 30
    msg.actions.append(of.ofp_action_output(port = switches[switchID][dst_mac])) # set the output port to what was stored in the switch table
    msg.data = event.ofp # load in the payload
    event.connection.send(msg) # send the flow to the switch

def _handle_Connection_Up(event):
  '''
  Handler for the Connection_Up event
  '''
  msg = of.ofp_flow_mod() # new flow message
  msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD)) # flood the network so that the network is all set up when it is first run
  event.connection.send(msg) # sends the flow

def launch ():
  core.openflow.addListenerByName("PacketIn", _handle_PacketIn) # set the PacketIn listener to the _handle_PacketIn method we created
  core.openflow.addListenerByName("ConnectionUp", _handle_Connection_Up) # set the ConnectionUp listener to the _handle_Connection_Up method we created
  log.info("Pair-Learning switch running.")
