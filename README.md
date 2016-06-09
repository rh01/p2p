dpdgsp: a P2P file sharing application with a centralized server
===

Dimitrios Paraschas
1562
Dimitrios Greasidis
1624
Stefanos Papanastasiou
1608


description
===

instructions
---

0. run make to clear the program configuration and clients database

1. run "run_server.sh" (./run_server.sh)

2. run at least two clients (from different terminals)
    e.g. run "run_u1.sh" and "run_u2.sh" (./run_u1.sh and ./run_u2.sh)

3. follow the menu instructions to test and use the program



protocol design
===
The protocol is designed to work on the application level with messages
transported over TCP ephemeral connections.


COMMANDS
---

OK : generic confirmation
ERROR : generic error reply


CLIENT -> SERVER
---

1. register connection

1.1. the client is connecting to the server for the first time

c: HELLO
s: AVAILABLE <username>
c: IWANT <username>
s: WELCOME <username>
s: AVAILABLE <username>
etc.

After the client has a TCP connection with the server, it sends the greeting
message "HELLO". The server generates and sends a new unique username with
the pattern "u#", where # is a incrementing integer, starting from 1, for use
as default by the client, using the format "AVAILABLE <username>". The client
chooses whether to accept the default username or use a different one. In both
cases, it sends the message "IWANT <username>". The server verifies that
the username the client send has not already been registed by a client, and
if so, replies with "WELCOME <username>". If the username choosen by the client
is taken the server replies with another "AVAILABLE <username>" message and
so on until a valid username is agreed on.



1.2. the client is known to the server, i.e. has already registered a username

c: HELLO <username>
s: WELCOME <username>

If the client has already registered a username with the server, the greeting
message includes the username. The server replies with a "WELCOME <username>"
message after it verifies that the username is valid.

In case the client sends an invalid username the server replies with an ERROR
message.

c: HELLO <username>
s: ERROR



2. send listening IP address and port

c: LISTENING <listening_ip> <listening_port>
s: OK

The client specifies the IP address and port that it is listening for incoming
connections. The server replies with a confirmation message.



3. send list of shared files

c: LIST <number_of_files> [\n<file_a>] [\n<file_b>] [...]
s: OK

The client sends a list with the files it is sharing using a message with both
a header and a body. The header has the format "LIST <number_of_files>", where
number_of_files is the number of files that the client is sharing, and the body
contains the list of files, one file per line. The server parses the list of
files, verifies that the number_of_files is valid and stores the list for other
clients.



4. request list of shared files

c: SENDLIST
s: FULLLIST <number_of_files> [\n<client_a> <file_a>] [\n<client_a> <file_b>]

The client requests the full list of the clients that are connected to
the server. The list contains the names of clients and their files. The client
sends "SENDLIST" and the repsonse from the server is: "FULLLIST ...".
The command FULLLIST contains the number of files that exist, and the clients
with their files.



5. Request the IP address and port of the peer to connect to.

c: WHERE <peer_username>
s: AT <peer_IP_address> <peer_port>

The client sends the command WHERE and the username of the client that wishes
to connect and take a specific file. Server responds with command:
AT <peer_IP_address> <peer_port> which is the ip address of this client and
his port.

In case the peer_username doesn't exist the server responds with the command
UNKNOWN.

c: WHERE <peer_username>
s: UNKNOWN



6.
c: <invalid message>
s: ERROR

If in any case an invalid message sent to client or to server, the answer is
ERROR.



CLIENT -> CLIENT
---

7.
c: GIVE <filename>
p: TAKE <file_size>
p: <file buffer>
c: THANKS

When the connection client to client is initialized, the "receiver" sends
command GIVE <filename> and requests the spesific file from the "giver".
"Giver" sends TAKE following from the file size of the spesific file. After that
a message with the file it is sent from the "giver". "Receiver" responds with
THANKS if everything goes straight.

If the file doesn't exist the peer replies with an ERROR message.

c: GIVE <filename>
p: ERROR


notes
---
'c' :  client
's' :  server
'p' :  peer

All commands are terminated with a newline (\n) and the null character (\0).
