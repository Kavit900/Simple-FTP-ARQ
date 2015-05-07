import socket
import sys
import pickle
import signal
import threading
import os
from multiprocessing import Lock
from collections import namedtuple
import time



server_hostname = sys.argv[1]

server_port = int(sys.argv[2])
#SERVER_PORT = 7736

# Acknowledgement server hostname and port
ACK_HOST = socket.gethostname()
ACK_PORT = 10000

# Filename
file_location = sys.argv[3]

# Window Size N
N = int(sys.argv[4])
#N = 5

# MSS
MSS = int(sys.argv[5])
#MSS = 5


TYPE_DATA = "0101010101010101"
TYPE_ACK = "1010101010101010"
TYPE_EOF = "1111111111111111"


data_packet = namedtuple('data_packet', 'sequence_no checksum type data')
ack_packet = namedtuple('ack_packet', 'sequence_no padding type')


thread_lock = Lock()


window_floor = 0
window_ceil = N - 1


piped_packet = 0


ACK = 0


RTT = 1


completed = False



def compchecksum(data):
    return 0xfff



def send_packet(sequence_number):
    print("Sending packet =", sequence_number)
    
    client_socket.sendto(preprocessed_packet_data[sequence_number], (server_hostname, server_port))
    time.sleep(0.5)


def signal_handler(signum, frame):
    global ACK, window_ceil, window_floor, RTT, packets_length

    
    index = ACK
    
    if ACK == window_floor:
        
        print("Timeout, sequence number =", ACK)

        thread_lock.acquire()

        
        while index < window_ceil and index < packets_length:
            
            signal.alarm(0)
            signal.setitimer(signal.ITIMER_REAL, RTT)
            send_packet(index)
            index += 1
        thread_lock.release()



def prepare(mss):
    
    sequence_number = 0

   
    packets = list()

    
    for mss_data in mss:
        packet_checksum = compchecksum(mss_data)
        packet_attr_list = [sequence_number, packet_checksum, TYPE_DATA, mss_data]

        
        packet = pickle.dumps(packet_attr_list)

        
        packets.append(packet)

     
        sequence_number += 1

    return packets



def read_data(filename):
    mss_array = list()
   
    with open(filename, "rb") as f:

        while True:
           
            mss_bytes = f.read(MSS)

            
            if mss_bytes:
                mss_array.append(mss_bytes)
            else:
                break

    return mss_array



def rdt_send(client_socket):
    global preprocessed_packet_data, packets_length, piped_packet

    
    max_window = min(N, packets_length)
    while piped_packet < max_window:
        
        if ACK == 0:
            send_packet(piped_packet)
            piped_packet += 1
        else:
            break



def acknowledgement_handler():
    print("acknowledgement_handler started")
    global window_ceil, window_floor, packets_length, piped_packet, ACK, completed

    
    ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ack_sock.bind((ACK_HOST, ACK_PORT))
    
    while True:
        
        server_message = ack_sock.recv(65535)
        print "Server message is %s" % server_message
        
        fields = pickle.loads(server_message)
        

        
        if fields[2] == TYPE_ACK:
            
            ACK = fields[0]
            
            if ACK:
                print "ACK is %s" % ACK
                
                thread_lock.acquire()

                
                if ACK == packets_length:
                    print("All packets sent!")
                    thread_lock.release()
                    completed = True
                    break

                
                elif packets_length > ACK >= window_floor:
                 
                    signal.alarm(0)
                    signal.setitimer(signal.ITIMER_REAL, RTT)

                    
                    number_of_acked = ACK - window_floor
                    window_floor = ACK

                    
                    outdate_ceil = window_ceil
                    window_ceil = min(window_ceil + number_of_acked, packets_length - 1)

                    
                    for i in range(window_ceil - outdate_ceil):
                        send_packet(piped_packet)
                        if piped_packet < packets_length - 1:
                            piped_packet += 1

                    thread_lock.release()


# Create a UDP client socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Get the mss_byte_array of the given file
mss_byte_array = read_data(file_location)


preprocessed_packet_data = prepare(mss_byte_array)


packets_length = len(preprocessed_packet_data)


window_ceil = min(N, packets_length) - 1


signal.signal(signal.SIGALRM, signal_handler)


acknowledgement_thread = threading.Thread(target=acknowledgement_handler)
acknowledgement_thread.start()


rdt_send(client_socket)



while not completed:
    pass


acknowledgement_thread.join()
client_socket.close()
