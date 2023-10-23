#!/usr/bin/env python3

"""
    Python 3
    Usage: ./client.py server_IP server_port client_udp_server_port
    coding: utf-8

    Client program for EdgeNet.
    
    Adapted from Sample code for Multi-Threaded Client by Wei Song.
"""

from socket import *
import sys
import os
from threading import Thread
from time import sleep
from constants import   LOCALHOST, BUFFER_SIZE, VALID_OPERATIONS, PROMPT, \
                        SERVER_SUCCESS

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} server_IP server_port client_udp_server_port")
    exit(0)

try:
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    client_udp_server_port = int(sys.argv[3])
except ValueError:
    print(f"Usage: {sys.argv[0]} server_IP server_port client_udp_server_port")
    exit(0)

# Defining a client socket to communicate with the server and building a 
# connection
client_socket = socket(AF_INET, SOCK_STREAM)
try:
    client_socket.connect((server_host, server_port))
except ConnectionRefusedError:
    print(f"Connection refused by server. Is the server running?")
    exit(1)

# Checking udp server socket isn't in use already
peer_sock = socket(AF_INET, SOCK_DGRAM)
try:
    peer_sock.bind((LOCALHOST, client_udp_server_port))
except OSError:
    print(f"Client UDP server port {client_udp_server_port} is already in use. Please choose another port")
    exit(1)
finally:
    peer_sock.close()

# Checks that a given string is a positive integer and converts it to an integer
# Returns None and prints error if the string is not a positive integer
def get_positive_int(prefix, name, string):
    try:
        string = int(string)
    except ValueError:
        print(f"{prefix}: {name} must be an integer! You entered {string}")
        return

    if string <= 0:
        print(f"{name} must be positive!")
        return
    
    return string

# UDP listener thread to download files from peers
def peer_receiver_loop():
    while True:
        peer_sock = socket(AF_INET, SOCK_DGRAM)
        try:
            peer_sock.bind((LOCALHOST, client_udp_server_port))
        except OSError:
            print(f"Client UDP server port {client_udp_server_port} is already in use. Please choose another port")
            os._exit(1)
        
        data, _ = peer_sock.recvfrom(BUFFER_SIZE)
        username = data.strip().decode()

        data, _ = peer_sock.recvfrom(BUFFER_SIZE)
        filename = data.strip().decode()

        new_filename = f"{username}_{filename}"

        print()
        print(f"File {filename} being received from someone")

        with open(new_filename, "wb") as f:
            data, _ = peer_sock.recvfrom(BUFFER_SIZE)
            try:
                while data:
                    f.write(data)
                    peer_sock.settimeout(2)
                    data, _ = peer_sock.recvfrom(BUFFER_SIZE)
            except timeout:
                peer_sock.close()
        
        print(f"Saved file {filename} as {new_filename} from {username}")
        print(PROMPT)

# Starting UDP listener as separate deamon thread
listen_UDP = Thread(target=peer_receiver_loop)
listen_UDP.setDaemon(True)
listen_UDP.start()

# Gets peer IP and UDP port from server and sends file directly to peer
def send_file_to_peer(device_name, filename):
    response = send_to_server(f"device address\n{device_name}").splitlines()

    if response[0] == "device not found":
        print(f"Device with name {device_name} does not exist")
        return
    
    if response[0] == "device not active":
        print(f"Device with name {device_name} is offline")
        return

    if not os.path.exists(filename):
        print(f"The file to be sent does not exist!")
        return

    print(f"Sending file to {device_name} at {response[1]}:{response[2]}")

    host = response[1]
    port = int(response[2])

    peer_socket = socket(AF_INET, SOCK_DGRAM)
    peer_socket.sendto(username.encode(), (host, port))
    peer_socket.sendto(filename.encode(), (host, port))
    
    with open(filename, "rb") as f:
        data = f.read(BUFFER_SIZE)
        while data:
            # Sending BUFFER_SIZE bytes of file to peer at a time
            if peer_socket.sendto(data, (host, port)):
                data = f.read(BUFFER_SIZE)
            # Throttling send to not overload receiver
            sleep(0.0002)

    print(f"File {filename} has been sent to {device_name}")
    
    peer_socket.close()

# Generating sample data when EDG command is called
def generate_data(fileID, dataAmount):
    fileID = get_positive_int("EDG", "fileID", fileID)
    
    if fileID is None:
        return

    dataAmount = get_positive_int("EDG", "dataAmount", dataAmount)
    
    if dataAmount is None:
        return
    
    print(f"The edge device is generating {dataAmount} data samples...")

    filename = f"{username}-{fileID}.txt"

    with open(filename, "w") as f:
        for i in range(dataAmount):
            f.write(str(i + 1) + "\n")
    
    print(f"Data generation done, {dataAmount} data samples have been generated and stored in the file {filename}")

# Uploads a file to the server with ID fileID
def upload_file(fileID):
    fileID = get_positive_int("UED", "fileID", fileID)
    
    if fileID is None:
        return

    filename = f"{username}-{fileID}.txt"
    try:
        with open(filename, "r") as f:
            data = f.read()
    except FileNotFoundError:
        print(f"The file to be uploaded does not exist!")
        return
    
    send_to_server(f"ued\n{fileID}")
    response = send_to_server(data)

    if response == SERVER_SUCCESS:
        print(f"File {filename} has been uploaded to the central server")
    else:
        print(f"There was an error uploading file to the central server...")

# Deletes a file from the server with ID fileID
def delete_file(fileID):
    fileID = get_positive_int("DTE", "fileID", fileID)
    
    if fileID is None:
        return
    
    response = send_to_server(f"dte\n{fileID}")

    if response == SERVER_SUCCESS:
        print(f"Data file with ID of {fileID} has been deleted")
    elif response == "file not found":
        print(f"File with ID of {fileID} does not exist on central server")

# Requests the server to compute an operation on a file on the server with ID 
# fileID and the given operation (either sum, average, min or max), returning
# the result
def compute_file(fileID, computation_operation):
    computation_operation = computation_operation.lower()

    fileID = get_positive_int("EDG", "fileID", fileID)

    if fileID is None:
        return

    if computation_operation not in VALID_OPERATIONS:
        print(f"Invalid computation operation")
        return

    response = send_to_server(f"scs\n{fileID}\n{computation_operation}")

    if response == "file not found":
        print(f"File with ID of {fileID} does not exist on central server")
    else:
        print(f"The result of {computation_operation} on file {fileID} is {response.split()[1]}")

# Sends a message to the server and returns the response back from server
def send_to_server(message):
    client_socket.sendall(message.encode())
    data = client_socket.recv(BUFFER_SIZE).decode()
    return data

def get_aed():
    response = send_to_server("aed")
    
    if response == "no other aed":
        print("There are no other active edge devices")
    else:
        print(response)

# USER LOGIN SEQUENECE
# Ensuring username is not empty
username = ""
while not username:
    username = input("Username: ")
response = ''

# Propting for credentials until the user is authenticated
while response != SERVER_SUCCESS:
    # Ensuring password is not empty
    password = ""
    while not password:
        password = input("Password: ")

    response = send_to_server(f"login request\n{username}\n{password}")
    if response == 'invalid password':
        print("Invalid Password. Please try again")
    if response == 'invalid password account blocked':
        print("Invalid Password. Your account has been blocked. Please try again later")
        client_socket.close()
        exit(0)
    if response == 'account blocked':
        print("Your account is blocked due to multiple authentication failures. Please try again later")
        client_socket.close()
        exit(0)

# Sending UPD listening port to server
send_to_server(f"udp port\n{client_udp_server_port}")

print("Welcome!")

# MAIN LOOP
while True:
    message = input(PROMPT).split()

    if len(message) == 0:
        continue

    command = message[0].upper()
    num_args = len(message) - 1

    # Process vaild commands and check for correct number of arguments
    if command == "EDG":
        if num_args < 2:
            print("EDG: fileID or dataAmount is missing!")
        elif num_args > 2:
            print("EDG: too many arguments")
        else:
            generate_data(message[1], message[2])
    elif command == "UED":
        if num_args < 1:
            print("UED: a fileID is needed to upload the data")
        elif num_args > 1:
            print("UED: too many arguments")
        else:
            upload_file(message[1])
    elif command == "DTE":
        if num_args < 1:
            print("DTE: a fileID is needed to delete the file")
        elif num_args > 1:
            print("DTE: too many arguments")
        else:
            delete_file(message[1])
    elif command == "SCS":
        if num_args < 2:
            print("SCS: fileID or computationOperation is missing!")
        elif num_args > 2:
            print("SCS: too many arguments")
        else:
            compute_file(message[1], message[2])
    elif command == "AED":
        if num_args > 0:
            print("AED: no arguments expected")
        else:
            get_aed()
    elif command == "UVF":
        if num_args < 2:
            print("UVF: deviceName or filename is missing!")
        elif num_args > 2:
            print("UVF: too many arguments")
        else:
            send_file_to_peer(message[1], message[2])
    elif command == "OUT":
        if num_args > 0:
            print("OUT: no arguments expected")
        else:
            print(f"Bye, {username}!")
            break
    else:
        print("Error. Invalid command!")


client_socket.close()
