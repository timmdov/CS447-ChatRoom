# connection.py
"""
    Connection Manager is responsible for managing client connections.
"""
class ConnectionManager:
    def __init__(self):
        self.connections = {}

    def add_connection(self, client, nickname, address, public_key=None):
        self.connections[client] = {
            'nickname': nickname,
            'address': address,
            'public_key': public_key
        }

    def remove_connection(self, client):
        if client in self.connections:
            del self.connections[client]

    def get_client_by_nickname(self, nickname):
        for client, details in self.connections.items():
            if details['nickname'] == nickname:
                return client, details
        return None, None

    def get_all_clients_except(self, exclude_client):
        return [client for client in self.connections.keys() if client != exclude_client]

    def get_nickname(self, client):
        if client in self.connections:
            return self.connections[client]['nickname']
        return None
