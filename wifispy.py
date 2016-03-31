import sys
import os
import random
import time
import multiprocessing
import pcapy
import dpkt

# mac
interface = 'en0'
enable_monitor  = 'tcpdump -i en0 -Ic1 -py IEEE802_11'
disable_monitor = 'tcpdump -i en0 -Ic1'
change_channel  = 'airport -c{}'

# linux
# interface = 'wlan1mon'
# enable_monitor  = 'ifconfig wlan1 down; iw dev wlan1 interface add wlan1mon type monitor; ifconfig wlan1mon down; iw dev wlan1mon set type monitor; ifconfig wlan1mon up'
# disable_monitor = 'iw dev wlan1mon del; ifconfig wlan1 up'
# change_channel  = 'iw dev wlan1mon set channel {}'

channels = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 # 2.4GHz
    # 36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161 # 5GHz
]

def start():
    os.system(enable_monitor)
    rotator(channels, change_channel)
    try: sniff(interface)
    except KeyboardInterrupt as e: sys.exit(e)
    finally: os.system(disable_monitor)

def rotator(channels, change_channel):
    def hop():
        while True:
            try:
                channel = random.choice(channels)
                print('\nChanging to channel ' + str(channel) + '...\n')
                os.system(change_channel.format(channel))
                time.sleep(1) # seconds
            except BaseException as e: sys.exit(e)
    multiprocessing.Process(target=hop).start()

def to_address(address): # decode a MAC or BSSID address
    return ':'.join('%02x' % ord(b) for b in address)

def sniff(interface):
    max_packet_size = 256 # bytes
    promiscuous = 0 # boolean masquerading as an int
    timeout = 100 # milliseconds
    packets = pcapy.open_live(interface, max_packet_size, promiscuous, timeout)
    packets.setfilter('') # bpf syntax (empty string = everything)
    def loop(header, data):
        try:
            packet = dpkt.radiotap.Radiotap(data)
            frame = packet.data
            if frame.type == dpkt.ieee80211.MGMT_TYPE:
                subtype = str(frame.subtype)
                source_address = to_address(frame.mgmt.src)
                destination_address = to_address(frame.mgmt.dst)
                ap_address = to_address(frame.mgmt.bssid)
                ap_name = frame.ssid.data if hasattr(frame, 'ssid') else '(n/a)'
                print('[MANAGEMENT FRAME] ' + subtype + ' * ' + ap_name + ' * ' + source_address + ' => ' + destination_address)
            elif frame.type == dpkt.ieee80211.CTL_TYPE:
                subtype = str(frame.subtype)
                print('[CONTROL FRAME] ' + subtype)
            elif frame.type == dpkt.ieee80211.DATA_TYPE:
                subtype = str(frame.subtype)
                source_address = to_address(frame.data_frame.src)
                destination_address = to_address(frame.data_frame.dst)
                ap_address = to_address(frame.data_frame.bssid) if hasattr(frame.data_frame, 'bssid') else '(n/a)'
                print('[DATA FRAME] ' + subtype + ' * ' + ap_address + ' * ' + source_address + ' => ' + destination_address)
        except:
            print('[COULD NOT PARSE PACKET]')
    packets.loop(-1, loop)

start()
