#!/usr/bin/env python3

"""
    Python 3
    Usage: ./server.py server_port number_of_consecutive_failed_attempts
    Coding: utf-8

    Server program for EdgeNet.
    
    Adapted from Sample code for Multi-Threaded Server by Wei Song.
"""

from socket import *
from threading import Thread
import sys
from time import time, strftime
import os
from constants import   BUFFER_SIZE, LOCALHOST, CREDENTIALS_FILENAME, \
                        ED_LOG_FILENAME, UPLOAD_LOG_FILENAME, \
                        DELETION_LOG_FILENAME, SERVER_SUCCESS

active_edge_devices = []

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} server_port number_of_consecutive_failed_attempts")
    exit(0)

try:
    server_host = LOCALHOST
    server_port = int(sys.argv[1])
except ValueError:
    print(f"Usage: {sys.argv[0]} server_port number_of_consecutive_failed_attempts")
    exit(0)


# Clearing log files on server startup
with open(ED_LOG_FILENAME, "w"):
    pass

with open(UPLOAD_LOG_FILENAME, "w"):
    pass

with open(DELETION_LOG_FILENAME, "w"):
    pass

# Building the active edge devices file
def make_log_file():
    with open(ED_LOG_FILENAME, "w") as f:
        for i, device in enumerate(active_edge_devices):
            f.write(f"{i + 1}; {device['active_since']}; {device['username']}; {device['ip']}; {device['udp_port']}\n")

try:
    max_consecutive_failed_attempts = int(sys.argv[2])
    if max_consecutive_failed_attempts < 1 or max_consecutive_failed_attempts > 5:
        raise ValueError
except ValueError:
    print(f"Invalid number of allowed failed consecutive attempts: {sys.argv[2]}. The valid value of argument number is an integer between 1 and 5")
    exit(0)

server_socket = socket(AF_INET, SOCK_STREAM)

try:
    server_socket.bind((server_host, server_port))
except OSError:
    print(f"Cannot bind to port {server_port}! Try another...")
    exit(1)

users = {}

# Reading credentials from file and storing in a dictionary
with open(CREDENTIALS_FILENAME, "r") as f:
    for line in f:
        line = line.split()
        users[line[0]] = {
            "password": line[1],
            "consecutive_failed_attempts": 0,
            "blocked_until": time()
        }

def generate_timestamp():
    return strftime("%-d %B %Y %H:%M:%S")

# Multi-thread class for client connections
class ClientThread(Thread):
    def __init__(self, client_address, client_socket):
        Thread.__init__(self)
        self.client_address = client_address
        self.client_socket = client_socket
        self.username = ''
        self.authenticated = False
        self.clientAlive = True
        
    def run(self):
        message = ''
        
        # Main loop for client connection, listening for client commands
        while self.clientAlive:
            data = self.client_socket.recv(BUFFER_SIZE).decode()

            if data == '':
                if not self.authenticated:
                    break

                self.clientAlive = False
                self.print_command_message("OUT")

                for device in active_edge_devices:
                    if device.get("username") == self.username:
                        active_edge_devices.remove(device)
                        break

                make_log_file()

                print(f"{self.username} exited the edge network")
                
                break
            
            message = ''

            commands = data.splitlines()
            command = commands[0]

            if command == 'login request':
                message = self.process_login(commands[1], commands[2])
            elif command == 'udp port':
                message = self.post_login(commands[1])
            elif not self.authenticated:
                print(f"\n--- {self.client_address} tried to perform unauthorised action ---")
                message = 'not authenticated'
            elif command == 'ued':
                message = self.save_file_from_client(commands[1])
            elif command == 'scs':
                message = self.compute_file_from_server(commands[1], commands[2])
            elif command == 'dte':
                message = self.delete_file_from_server(commands[1])
            elif command == 'aed':
                message = self.active_devices()
            elif command == 'device address':
                message = self.device_address(commands[1])
            else:
                print("[received] " + data)
                print("[sending] message could not be understood")
                message = 'message could not be understood'

            self.client_socket.send(message.encode())
    
    def print_command_message(self, command):
        print(f"\n--- User {self.username} issued {command} command ---")

    # Saves data from an client file with ID fileID to the server
    def save_file_from_client(self, fileID):
        self.print_command_message("UED")

        print(f"A data file is being received from edge device {self.username}...")
        filename = f"{self.username}-{fileID}.txt"
        self.client_socket.send(SERVER_SUCCESS.encode())

        data = b''
        chunk = self.client_socket.recv(BUFFER_SIZE)
        while chunk:
            try:
                data += chunk
                self.client_socket.settimeout(1)
                chunk = self.client_socket.recv(BUFFER_SIZE)
            except timeout:
                self.client_socket.settimeout(None)
                break
        
        data = data.decode()
        data_amount = len(data.splitlines())

        with open(filename, "w") as f:
            f.write(data)
        
        with open(UPLOAD_LOG_FILENAME, "a") as f:
            f.write(f"{self.username}; {generate_timestamp()}; {fileID}; {data_amount}\n")

        print(f"The file with ID {fileID} has been received and {UPLOAD_LOG_FILENAME} file has been updated")

        return SERVER_SUCCESS
    
    # Deletes an uploaded client file with ID fileID from the server
    def delete_file_from_server(self, fileID):
        self.print_command_message("DTE")
        filename = f"{self.username}-{fileID}.txt"
        
        if os.path.exists(filename):
            print(f"File {filename} was found, deleting...")
            
            with open(filename, "r") as f:
                data_amount = len(f.readlines())
            
            os.remove(filename)
            with open(DELETION_LOG_FILENAME, "a") as f:
                f.write(f"{self.username}; {generate_timestamp()}; {fileID}; {data_amount}\n")
            
            print(f"File with ID {fileID} has been deleted and {DELETION_LOG_FILENAME} file has been updated")
            return SERVER_SUCCESS
        else:
            print("File was not found, informing user")
            return 'file not found'
    
    # Performs computation on uploaded client file with ID fileID and sends the 
    # result back to the client
    def compute_file_from_server(self, fileID, computation_operation):
        self.print_command_message("SCS")
        filename = f"{self.username}-{fileID}.txt"
        
        if os.path.exists(filename):
            print(f"File {filename} was found, computing {computation_operation} operation...")
            file_data = open(filename, "r").readlines()
            numeric_data = [int(n) for n in file_data]
            
            if computation_operation == "sum":
                result = sum(numeric_data)
            elif computation_operation == "average":
                result = sum(numeric_data) / len(numeric_data)
            elif computation_operation == "max":
                result = max(numeric_data)
            elif computation_operation == "min":
                result = min(numeric_data)
            
            print(f"Computation done, result was {result}")
            return f"result {result}"
        else:
            print("File was not found, informing user")
            return 'file not found'
    
    # Returns a list of active edge devices other than the one that requested it
    def active_devices(self):
        self.print_command_message("AED")

        result = ""

        for device in active_edge_devices:
            if device.get("username") != self.username:
                result += f"{device['username']}, active since {device['active_since']}. IP: {device['ip']}, UDP port: {device['udp_port']}.\n"
        
        if result == '':
            print("No other active edge devices found")
            result = 'no other aed'
        else:
            print("Active edge devices found, sending list to user")

        return result

    # Processing device address request from another edge device (for peer to 
    # peer communication)
    def device_address(self, device_name):
        print(f"\n--- {self.username} has requested the UDP port that {device_name} is listening on ---")

        if device_name not in users:
            print(f"{device_name} does not exist, informing user")
            return "device not found"

        for device in active_edge_devices:
            if device.get("username") == device_name:
                print(f"Port {device['udp_port']} found, sending to user")
                return f"device found\n{device['ip']}\n{device['udp_port']}"

        print(f"{device_name} is not active, informing user")
        return "device not active"
    
    # Receiving UDP port from client after successful authentication
    def post_login(self, udp_port):
        print(f"\n--- UDP port received from {self.username} ---")
        self.udp_port = udp_port

        active_edge_devices.append({
            "username": self.username,
            "active_since": generate_timestamp(),
            "ip": self.client_address[0],
            "udp_port": self.udp_port
        })
        
        make_log_file()

        return SERVER_SUCCESS
    
    # Processing login request from client
    def process_login(self, username, password):
        print(f"\n--- Login request from edge device {self.client_address} ---")

        message = 'invalid password'

        if self.username:
            print(f"User {username} is already logged in")

            message = SERVER_SUCCESS
        elif username in users:
            if users[username]["blocked_until"] > time():
                print(f"User {username} is blocked for {users[username]['blocked_until'] - time()} more seconds")

                message = 'account blocked'
            elif users[username]["password"] == password:
                print(f"User {username} has successfully logged in")

                self.username = username
                self.authenticated = True
                message = SERVER_SUCCESS
                users[username]["consecutive_failed_attempts"] = 0
            else:
                print(f"Edge device {self.client_address} has provided an incorrect passsword for user '{username}'")

                users[username]["consecutive_failed_attempts"] += 1
            
                if users[username]["consecutive_failed_attempts"] >= max_consecutive_failed_attempts:
                    print(f"User {username} has been blocked for 10 seconds!")

                    message = 'invalid password account blocked'
                    users[username]["consecutive_failed_attempts"] = 0
                    users[username]["blocked_until"] = time() + 10
        else:
            print(f"Edge device {self.client_address} has provided a non-existent user '{username}'")

        return message


print("--- Server Running ---")
print(f"IP: {server_host}")
print(f"Port: {server_port}")
print()

# Entry socket to create new threads for each client
while True:
    server_socket.listen()
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    client_socket, client_address = server_socket.accept()

    clientThread = ClientThread(client_address, client_socket)
    clientThread.setDaemon(True)
    clientThread.start()
