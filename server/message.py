# message.py

"""
    Manages and handles message delivery between clients in the chat system. (NOT IMPLEMENTED)
"""
from server.serverC import ChatServer


class MessageHandler:
    """ A list to temporarily store messages. """
    def __init__(self):
        self.connections = None
        self.message_queue = []
        self.chat_server = ChatServer()


    """ Sends a message to all clients except the sender. """
    def broadcast(self, message, sender=None):
        recipients = self.connections.get_all_clients_except(sender)
        for client in recipients:
            try:
                client.send(message)
            except:
                self.chat_server.remove_client(client)

    """ Sends a direct message to a specific recipient. """
    def private_message(self, message, sender, recipient):
        recipient.send('MESSAGE'.encode('ascii'))
        recipient.send(message)
