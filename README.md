# EdgeNet

A decentralised edge computing framework that allows edge devices to connect, upload, compute, and share data.

## Description

EdgeNet is a multi-threaded network framework designed to support edge computing devices. It promotes the collaboration of edge devices by providing functionalities such as data storage, computation on stored data, and peer-to-peer data sharing. Built on Python, EdgeNet makes use of both TCP and UDP sockets to maintain reliable connections, transfer large amounts of data, and handle multiple clients simultaneously.

## Features

- **User Authentication:** Login mechanism with a blocking feature after consecutive failed attempts.
- **File Management:** Edge devices can upload and delete files on the server.
- **Computation Service:** Server-side computation operations like sum, average, min, and max on uploaded files.
- **Peer-to-Peer Data Sharing:** Devices can directly share files with other active edge devices.
- **Active Devices Listing:** Any edge device can request a list of other active devices in the network.

## Prerequisites

- Python 3
- A Unix-based system (recommended)

## Usage

### Server

Start the server by running:

```
./server.py [server_port] [number_of_consecutive_failed_attempts]
```

Where:
- `server_port` is the port number you wish the server to listen on.
- `number_of_consecutive_failed_attempts` is the number of consecutive failed login attempts after which a user gets blocked.

### Client

Connect an edge device (client) by running:

```
./client.py [server_IP] [server_port] [client_udp_server_port]
```

Where:
- `server_IP` is the IP address of the server.
- `server_port` is the port number the server is listening on.
- `client_udp_server_port` is the UDP port the client wishes to use for peer-to-peer communications.

## Logging

The system maintains three types of log files:
1. Active edge devices log (`ED_LOG_FILENAME`).
2. Data upload log (`UPLOAD_LOG_FILENAME`).
3. Data deletion log (`DELETION_LOG_FILENAME`).
