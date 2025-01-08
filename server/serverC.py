import socket
import threading
import time
from encryption import ServerEncryption
from connection import ConnectionManager
from group_manager import GroupManager

class ChatServer:
    def __init__(self, host='0.0.0.0', port=55557, udp_port=55558):
        self.group_manager = GroupManager()
        self.TCP_PORT = port
        self.UDP_PORT = udp_port
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        
        self.connections = ConnectionManager()
        self.encryption = ServerEncryption()

    def handle_client(self, client):
        try:
            public_key, nickname, client_address = self.perform_handshake(client)
            self.connections.add_connection(client, nickname, client_address, public_key)
            
            try:
                self.broadcast(f"{nickname} joined!".encode('utf-8'), sender=client)
            except Exception as e:
                raise Exception(f"Error broadcasting join message: {e}")
                
            self.process_client_messages(client)
            
        except Exception:
            self.remove_client(client)
            
        finally:
            if client in self.connections.connections:
                self.remove_client(client)

    def perform_handshake(self, client):
        client.send('KEY'.encode('utf-8'))
        key_data = client.recv(2048)
        public_key = self.encryption.load_public_key(key_data)
        
        client.send('NICK'.encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')
        
        client_address = client.getpeername()
        return public_key, nickname, client_address

    def process_client_messages(self, client):
        buffer = b''
        while True:
            try:
                data = client.recv(8192)
                if not data:
                    break
                    
                buffer += data
                
                try:
                    if b'FILE:' in buffer:
                        header_end = buffer.find(b'\n')
                        if header_end != -1:
                            header = buffer[:header_end].decode('utf-8')
                            buffer = buffer[header_end + 1:]
                            
                            _, sender_nickname, file_name, file_size, file_extension = header.split(':')
                            file_size = int(file_size)
                            
                            self.broadcast(header.encode('utf-8') + b'\n', sender=client)
                            
                            total_received = len(buffer)
                            self.broadcast(buffer, sender=client)
                            
                            while total_received < file_size:
                                chunk = client.recv(min(8192, file_size - total_received))
                                if not chunk:
                                    break
                                total_received += len(chunk)
                                self.broadcast(chunk, sender=client)
                                
                            buffer = b''
                            continue

                    if b'VOICE:' in buffer:
                        header_end = buffer.find(b'\n')
                        if header_end != -1:
                            header = buffer[:header_end].decode('utf-8')
                            buffer = buffer[header_end + 1:]
                            
                            _, sender_nickname, audio_size = header.split(':')
                            audio_size = int(audio_size)
                            
                            self.broadcast(header.encode('utf-8') + b'\n', sender=client)
                            
                            total_received = len(buffer)
                            self.broadcast(buffer, sender=client)
                            
                            while total_received < audio_size:
                                chunk = client.recv(min(8192, audio_size - total_received))
                                if not chunk:
                                    break
                                total_received += len(chunk)
                                self.broadcast(chunk, sender=client)
                                
                            buffer = b''
                            continue
                    
                    message = buffer.decode('utf-8')
                    buffer = b''
                    
                    if message.startswith(('GROUP_CREATE:', 'GROUP_JOIN:', 'GROUP_LEAVE:', 'GROUP_MSG:')):
                        self.handle_group_message(message, client)
                    elif message.startswith('DISCOVER'):
                        self.handle_discover(client, message)
                    else:
                        self.broadcast(message.encode('utf-8'), sender=client)
                        
                except UnicodeDecodeError:
                    continue
                    
            except Exception:
                self.remove_client(client)
                break

    def handle_udp_discovery(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('0.0.0.0', self.UDP_PORT))
        print("Server running on UDP port", self.UDP_PORT)
        
        pending_connections = {}
        
        while True:
            try:
                data, addr = udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                
                try:
                    msg_data = eval(message)
                    if isinstance(msg_data, dict):
                        if msg_data.get('type') == 'discover':
                            target_nickname = msg_data.get('target')
                            target_client, details = self.connections.get_client_by_nickname(target_nickname)
                            
                            if target_client:
                                connection_id = f"{addr[0]}:{addr[1]}-{details['address'][0]}:{details['address'][1]}"
                                pending_connections[connection_id] = {
                                    'initiator': addr,
                                    'target': details['address'],
                                    'timestamp': time.time()
                                }
                                
                                peer1_info = f"PEER_INFO:{details['address'][0]}:{details['address'][1]}"
                                peer2_info = f"PEER_INFO:{addr[0]}:{addr[1]}"
                                
                                udp_socket.sendto(peer1_info.encode('utf-8'), addr)
                                if target_client:
                                    target_client.send(peer2_info.encode('utf-8'))
                                    
                        elif msg_data.get('type') == 'connection_status':
                            status = msg_data.get('status')
                            connection_id = msg_data.get('connection_id')
                            if connection_id in pending_connections:
                                del pending_connections[connection_id]
                                
                except Exception:
                    continue
                    
                current_time = time.time()
                expired_connections = [conn_id for conn_id, data in pending_connections.items() 
                                     if current_time - data['timestamp'] > 30]
                for conn_id in expired_connections:
                    del pending_connections[conn_id]
                    
            except Exception:
                continue

    def broadcast(self, message, sender=None):
        try:
            recipients = self.connections.get_all_clients_except(sender)
            disconnected_clients = []
            
            for client in recipients:
                try:
                    try:
                        client.getpeername()
                    except OSError:
                        disconnected_clients.append(client)
                        continue
                        
                    client.send(message)
                except Exception:
                    disconnected_clients.append(client)
            
            for client in disconnected_clients:
                self.remove_client_silent(client)
                
        except Exception:
            pass

    def remove_client(self, client):
        try:
            if client in self.connections.connections:
                nickname = self.connections.get_nickname(client)
                self.remove_client_silent(client)
                
                try:
                    self.broadcast(f"{nickname} left!".encode('utf-8'))
                except Exception:
                    pass
        except Exception:
            pass

    def remove_client_silent(self, client):
        try:
            if client in self.connections.connections:
                nickname = self.connections.get_nickname(client)
                for group_name in self.group_manager.get_user_groups(client):
                    self.group_manager.leave_group(group_name, client, nickname)
                
                self.connections.remove_connection(client)
                
                try:
                    client.close()
                except Exception:
                    pass
                    
        except Exception:
            pass

    def handle_discover(self, client, message):
        try:
            target_nickname = message.split(':')[1]
            target_client, details = self.connections.get_client_by_nickname(target_nickname)
            if target_client:
                peer_info = f"PEER_INFO:{details['address'][0]}:{details['address'][1]}"
                client.send(peer_info.encode('utf-8'))
            else:
                error_message = f"ERROR: User {target_nickname} not found."
                client.send(error_message.encode('utf-8'))
        except Exception:
            client.send("ERROR: Invalid discover format.".encode('utf-8'))

    def start(self):
        print("Server running...")
        udp_thread = threading.Thread(target=self.handle_udp_discovery)
        udp_thread.daemon = True
        udp_thread.start()
        
        while True:
            try:
                client, address = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(client,))
                thread.daemon = True
                thread.start()
            except Exception:
                continue

    def handle_group_message(self, message, client):
        try:
            cmd_parts = message.split(':', 2)
            if len(cmd_parts) < 2:
                return

            command = cmd_parts[0]
            group_name = cmd_parts[1]
            content = cmd_parts[2] if len(cmd_parts) > 2 else ""
            
            nickname = self.connections.get_nickname(client)
            if not nickname:
                return

            if command == 'GROUP_CREATE':
                success = self.group_manager.create_group(group_name, client, nickname)
                response = f"GROUP_INFO:{group_name}:{'created' if success else 'exists'}"
                client.send(response.encode('utf-8'))
                
                if success:
                    members = self.group_manager.get_group_nicknames(group_name)
                    self.broadcast_to_group(f"GROUP_MEMBERS:{group_name}:{','.join(members)}", group_name)
                    client.send(f"GROUP_UPDATE:{group_name}:Group created successfully".encode('utf-8'))

            elif command == 'GROUP_JOIN':
                success = self.group_manager.join_group(group_name, client, nickname)
                if success:
                    client.send(f"GROUP_INFO:{group_name}:joined".encode('utf-8'))
                    
                    members = self.group_manager.get_group_nicknames(group_name)
                    member_list_msg = f"GROUP_MEMBERS:{group_name}:{','.join(members)}"
                    
                    for member in self.group_manager.get_group_members(group_name):
                        try:
                            member.send(member_list_msg.encode('utf-8'))
                        except Exception:
                            pass
                    
                    join_msg = f"GROUP_UPDATE:{group_name}:{nickname} joined the group"
                    self.broadcast_to_group(join_msg, group_name, exclude_client=client)
                else:
                    client.send(f"GROUP_INFO:{group_name}:not found".encode('utf-8'))

            elif command == 'GROUP_MSG':
                if group_name in self.group_manager.groups:
                    group_message = f"GROUP_MSG:{group_name}:{nickname}: {content}"
                    
                    members = self.group_manager.get_group_members(group_name)
                    failed_members = []
                    
                    for member in members:
                        try:
                            member.send(group_message.encode('utf-8'))
                        except Exception:
                            failed_members.append(member)
                    
                    for failed_member in failed_members:
                        self.remove_client(failed_member)
                        self.group_manager.leave_group(group_name, failed_member, 
                                                    self.connections.get_nickname(failed_member))
                else:
                    client.send(f"ERROR: Group {group_name} does not exist".encode('utf-8'))

        except Exception:
            try:
                client.send("ERROR: Failed to process group command.".encode('utf-8'))
            except:
                pass

    def broadcast_to_group(self, message, group_name, exclude_client=None):
        try:
            members = self.group_manager.get_group_members(group_name)
            if not members:
                return
            
            failed_members = []
            for member in members:
                if member != exclude_client:
                    try:
                        member.send(message.encode('utf-8'))
                    except Exception:
                        failed_members.append(member)
            
            for failed_member in failed_members:
                nickname = self.connections.get_nickname(failed_member)
                self.group_manager.leave_group(group_name, failed_member, nickname)
                self.remove_client(failed_member)

        except Exception:
            pass

if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")