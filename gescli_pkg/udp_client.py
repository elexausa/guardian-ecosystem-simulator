import socket 

class UDP:

    def __init__(self):
        pass

    def send(self, command, ip, port):
        """Sends a command to the configured IP address and port.
        
        Args:
            command (str): Command to be sent.
        """

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(command.encode(), (ip, int(port)))
            sock.close()
        except Exception as e:
            print("Unable to send {command} => {error}".format(command=command,
                                                               error=e))
