#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import print_function
import logging
import os
import signal
import socket
import sys
from threading import Thread

from library.library import sigint_handler
from library.library import json_load
from library.library import json_save
from library.library import send_message


#DEBUG = True
DEBUG = False


configuration_file = ""
configuration = {}

clients_file = ""
# {username: {files: [shared files], listening_IP_address: listening_IP_address, listening_port: listening_port}}
clients = {}

# {(IP_address, port): username}
connected_clients = {}

#使用signal.signal()函数来预设(register)信号处理函数,signal.SIGINT为某个信号
signal.signal(signal.SIGINT, sigint_handler)


def converse(connection, client, incoming_buffer, own_previous_command):
    """
    handle messages, uses recursion if there are more incoming commands
    """

    global configuration_file
    global configuration
    global clients_file
    global clients
    global connected_clients

    if "\0" not in incoming_buffer:
        return "", own_previous_command
    else:
        index = incoming_buffer.index("\0")
        message = incoming_buffer[0:index-1]
        incoming_buffer = incoming_buffer[index+1:]

    # info message
    logging.info("message received: " + str(message))

    # split message into lines to handle them easier
    lines = message.split("\n")
    fields = lines[0].split()
    command = fields[0]

    if command == "HELLO":
        # check if there is a username after the command
        if len(fields) == 1:
            configuration["username_offset"] += 1
            json_save(configuration_file, configuration)

            # create available username for the new client
            username = "u{}".format(configuration["username_offset"])

            # send answer to client and call converse recursively
            send_message(connection, "AVAILABLE " + username + "\n\0")
            return converse(connection, client, incoming_buffer, "AVAILABLE")
        else:
            username = fields[1]
            if username in clients:
                # tie the client connection tuple with its username
                connected_clients[client] = username
                logging.debug("connected_clients: " + str(connected_clients))

                # send message WELCOME to client and call converse recursively
                send_message(connection, "WELCOME " + username + "\n\0")
                return converse(connection, client, incoming_buffer, "WELCOME")
            else:
                # otherwise send ERROR to client, don't need recursion here
                # because we don't wait for an incoming command from the client
                send_message(connection, "ERROR\n\0")
                return incoming_buffer, "ERROR"

    elif command == "IWANT":
        username = fields[1]
        # check if the username is valid
        if username in clients:
            configuration["username_offset"] += 1
            json_save(configuration_file, configuration)

            username = "u{}".format(configuration["username_offset"])

            # send answer to client and call converse recursively
            send_message(connection, "AVAILABLE " + username + "\n\0")
            return converse(connection, client, incoming_buffer, "AVAILABLE")
        else:
            clients[username] = {"files": [], "listening_ip": "", "listening_port": None}
            json_save(clients_file, clients)

            logging.debug("clients: " + str(clients))

            connected_clients[client] = username
            logging.debug("connected_clients: " + str(connected_clients))

            # send answer to client
            send_message(connection, "WELCOME " + username + "\n\0")
            return incoming_buffer, "WELCOME"

    elif command == "LISTENING":
        clients[connected_clients[client]]["listening_ip"] = fields[1]
        clients[connected_clients[client]]["listening_port"] = fields[2]
        json_save(clients_file, clients)
        logging.debug("clients: " + str(clients))

        # send answer to client
        send_message(connection, "OK\n\0")
        return incoming_buffer, "OK"

    elif command == "LIST":
        number_of_files = int(fields[1])
        if number_of_files != (len(lines) - 1):
            logging.warning("invalid LIST message, wrong number of files")

            send_message(connection, "ERROR\n\0")
            sys.exit(-1)
        else:
            clients[connected_clients[client]]["files"] = lines[1:]
            json_save(clients_file, clients)

        # send answer to client and call converse recursively
        send_message(connection, "OK\n\0")
        return incoming_buffer, "OK"

    elif command == "SENDLIST":
        number_of_all_clients_files = 0
        for client_ in clients:
            number_of_all_clients_files += len(clients[client_]["files"])
        fulllist_message = "FULLLIST {}\n".format(number_of_all_clients_files)
        for client_ in clients:
            for file_ in clients[client_]["files"]:
                fulllist_message += client_ + " " + file_ + "\n"
        fulllist_message += "\0"

        # sends list of clients and their files to the client that requested them
        send_message(connection, fulllist_message)
        return converse(connection, client, incoming_buffer, "FULLLIST")

    elif command == "WHERE":
        peer = fields[1]

        # search for the peer in the clients dictionary.
        # if valid, we sent to client the ip and port of the peer.
        if peer in clients:
            # get from dictionary ip and port
            peer_ip = clients[peer]["listening_ip"]
            peer_port = clients[peer]["listening_port"]

            # send message to client with ip and port of the client that
            # he wants to connect
            at_message = "AT {} {}\n\0".format(peer_ip, peer_port)

            send_message(connection, at_message)
            return incoming_buffer, "WHERE"
        else:
            send_message(connection, "UNKNOWN\n\0")
            return incoming_buffer, "UNKNOWN"

    elif command == "ERROR":
        logging.warning("ERROR message received, exiting")
        sys.exit(-1)

    else:
        # TODO
        # handle invalid commands
        logging.warning('an invalid command was received: "{}"'.format(command))
        sys.exit(-1)


def client_function(connection, address):
    """
    功能：
    receive messages and call the converse function to handle them
    参数说明：
    connection : connection socket
    address : (IP_address, port)
    """

    # start with an empty incoming messages buffer
    incoming_buffer = ""
    own_previous_command = ""

    while True:
        incoming = connection.recv(4096)
        if len(incoming) == 0:
            break
        else:
            incoming_buffer += incoming

        incoming_buffer, own_previous_command = converse(connection, address, incoming_buffer, own_previous_command)


def main():
    global configuration_file
    global configuration
    global clients_file
    global clients

    # basicConfig函数用来配置RootLogger
    # 支持六个关键字参数，分别为filename，filemode，stream，format，datefmt，level
    logging.basicConfig(level=logging.DEBUG,
            format="[%(levelname)s] (%(threadName)s) %(message)s",
            filename="server.log",
            filemode="w")
    # 创建一个handler，用于输出到控制台  
    console = logging.StreamHandler()
    
    if DEBUG:
        # 指定console被处理的信息级别为DEBUG，低于DEBUG级别的信息将被忽略
        console.setLevel(logging.DEBUG)
    else:
        # 指定console被处理的信息级别为INFO，低于INFO级别的信息将被忽略
        console.setLevel(logging.INFO)

    # 定义handler的输出格式
    formatter = logging.Formatter("[%(levelname)s] (%(threadName)s) %(message)s")
    console.setFormatter(formatter)

    # 定义RootLogger,给RootLogger添加handler  
    logging.getLogger("").addHandler(console)


    configuration_file = "configuration.json"
    clients_file = "clients.json"

    if os.path.isfile(configuration_file):
	# 从json文件中读入配置，并将其解码
        configuration = json_load(configuration_file)
    else:
	# 创建并初始化配置文件，将字典解码格式化保存到配置文件中
        configuration["host"] = "localhost"
        configuration["port"] = 45000
        configuration["username_offset"] = 0
        json_save(configuration_file, configuration)

    
    logging.debug("configuration: " + str(configuration))

    # load the list of known clients from the json file
    if os.path.isfile(clients_file):
        clients = json_load(clients_file)
    else:
        json_save(clients_file, clients)

    logging.debug("clients: " + str(clients))

    # 创建socket
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        logging.error("socket.socket error")
        sys.exit(-1)

    host = configuration["host"]
    port = configuration["port"]
    # 绑定socket
    try:
        server_socket.bind( (host, port) )
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except socket.error:
        # cli_output
        logging.error("port {} in use, exiting".format(port))
        sys.exit(-1)

    # 开启监听，监听接入连接的主机
    server_socket.listen(5)
    # 控制台输出
    # 输出消息
    logging.info("server listening on {}:{}".format(host, str(port)))

    # 对连接到服务器的主机进行下一步的处理
    client_counter = 0
    while True:
        connection, address = server_socket.accept()
        # cli_output
        # output message
        logging.info("a client connected from {}:{}".format(address[0], str(address[1])))

        # create a thread that runs the client_function
	# 设置实现的线程函数的名字，格式为client 1，client 2，...default:Thread-1,Thread-2
        client_thread = Thread(name="client {}".format(client_counter),
                target=client_function, args=(connection, address))

        # TODO
	# 设置daemon模式，即使主程序结束，这个子线程依然存在
        # handle differently, terminate gracefully
        client_thread.daemon = True
        client_thread.start()

        client_counter += 1


if __name__ == "__main__":
    main()
