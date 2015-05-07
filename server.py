import socket
import pickle
import random
import sys
import time


SERVER_PORT = int(sys.argv[1])
SERVER_FILE_NAME = sys.argv[2]
PROBABILITY_LOSS = float(sys.argv[3])


DATA_TYPE = "0101010101010101"
ACK = "1010101010101010"
END = "1111111111111111"
PADDING = "0000000000000000"

client_ack_port = 10000

def compchecksum(data):
    return 0xfff

# Locally running will work but for remote connection ender IP address manually
HOST = socket.gethostname()#socket.gethostname())
#HOST = '192.168.0.9' 
print HOST


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, SERVER_PORT))


next_sequence_num = 0


def send_ack(ack_packet, host):
    ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    #h1 = '152.46.18.151'
    ack_socket.sendto(ack_packet, (HOST, client_ack_port)) # change during demo to IP address.
    time.sleep(0.2)
    ack_socket.close()

while True:
    data_recv, address = server_socket.recvfrom(65535)

    data = pickle.loads(data_recv)


    sequence_number, checksum, type, mss = data[0], data[1], data[2], data[3]
    print(sequence_number, checksum, type, mss)

  
    if type == END:
        print("Received File!")
        print("Closing Socket")
        server_socket.close()
        break

    if type == DATA_TYPE:
        rprob = random.random()
        if rprob < PROBABILITY_LOSS :
            print("Packet loss, sequence number =" + str(sequence_number))

        else:
            if checksum != compchecksum(mss):
                print("Packet dropped, checksum doesnt match, sequence number =" + str(sequence_number))
            if next_sequence_num == sequence_number:
                acknowledgement = sequence_number + 1
                ack_packet = [acknowledgement, PADDING, ACK]
                #print "ack is %d before dumps" % acknowledgement
                ack_packet = pickle.dumps(ack_packet)
                #print "ack packet is %s" % ack_packet
                send_ack(ack_packet, address[0])

                with open(SERVER_FILE_NAME, 'ab') as file:
                        file.write(mss)

                next_sequence_num += 1

            elif next_sequence_num < sequence_number:
                print("Not Received sequence number" + str(next_sequence_num))
                acknowledgement = next_sequence_num
                ack_packet = [acknowledgement, PADDING, ACK]

                ack_packet = pickle.dumps(ack_packet)
                send_ack(ack_packet, address[0])
