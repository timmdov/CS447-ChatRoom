import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import time
import os
from encryption import ClientEncryption
import sys
import subprocess
from voice import VoiceRecorder, VoicePlayer

class ChatClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.encryption = ClientEncryption()
        self.socket.connect(('51.20.191.169', 55557))
        
        self.udp_socket = None
        self.peer_connections = {}
        self.local_udp_port = None
        
        self.nickname = input("Choose your nickname: ")
        self.setup_gui()
        self.setup_voice_chat()  
        self.running = True
        self.setup_udp_socket()
        self.start()

    def setup_udp_socket(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', 0))
        self.local_udp_port = self.udp_socket.getsockname()[1]
        self.udp_socket.settimeout(1)

    def setup_gui(self):
        self.window = tk.Tk()
        self.window.title(f"Chat - {self.nickname}")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.chat_frame = tk.Frame(self.window)
        self.chat_frame.pack(expand=True, fill='both')

        self.text_area = scrolledtext.ScrolledText(self.chat_frame)
        self.text_area.pack(expand=True, fill='both')

        self.input_area = tk.Entry(self.window)
        self.input_area.pack(fill='x', padx=10, pady=5)
        self.input_area.bind('<Return>', lambda e: self.send_message())

        self.buttons_frame = tk.Frame(self.window)
        self.buttons_frame.pack(fill='x', padx=10)

        self.send_button = tk.Button(self.buttons_frame, text="Send", command=self.send_message)
        self.send_button.pack(side='left', pady=5, padx=5)

        self.file_button = tk.Button(self.buttons_frame, text="Send File", command=self.send_file)
        self.file_button.pack(side='left', pady=5, padx=5)

        self.discover_frame = tk.Frame(self.window)
        self.discover_frame.pack(fill='x', padx=10)

        self.discover_label = tk.Label(self.discover_frame, text="Discover Peer:")
        self.discover_label.pack(side='left', pady=5)

        self.discover_input = tk.Entry(self.discover_frame)
        self.discover_input.pack(side='left', fill='x', expand=True, padx=5, pady=5)

        self.discover_button = tk.Button(self.discover_frame, text="Discover", command=self.initiate_discovery)
        self.discover_button.pack(side='left', pady=5)

        self.group_frame = tk.Frame(self.window)
        self.group_frame.pack(fill='x', padx=10)
        
        self.group_name_entry = tk.Entry(self.group_frame)
        self.group_name_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        self.create_group_button = tk.Button(self.group_frame, text="Create Group", command=self.create_group)
        self.create_group_button.pack(side='left', pady=5)
        
        self.join_group_button = tk.Button(self.group_frame, text="Join Group", command=self.join_group)
        self.join_group_button.pack(side='left', pady=5)
        
        self.current_group = None
        self.group_var = tk.StringVar(value="Global")
        self.group_menu = tk.OptionMenu(self.buttons_frame, self.group_var, "Global")
        self.group_menu.pack(side='left', pady=5, padx=5)
        
        self.groups = {"Global": {"members": set()}}

    def send_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("All Files", "*.*"),
                ("PDF Files", "*.pdf"),
                ("Text Files", "*.txt"),
                ("Image Files", "*.png *.jpg *.jpeg")
            ]
        )
        
        if file_path:
            try:
                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)
                file_extension = os.path.splitext(file_name)[1].lower()
                
                progress_label = tk.Label(self.window, text=f"Sending {file_name}...")
                progress_label.pack()
                
                try:
                    header = f"FILE:{self.nickname}:{file_name}:{file_size}:{file_extension}\n".encode('utf-8')
                    self.socket.sendall(header)
                    
                    time.sleep(0.1)
                    
                    bytes_sent = 0
                    chunk_size = 8192
                    with open(file_path, 'rb') as file:
                        while True:
                            chunk = file.read(chunk_size)
                            if not chunk:
                                break
                            self.socket.sendall(chunk)
                            bytes_sent += len(chunk)
                            progress = (bytes_sent / file_size) * 100
                            progress_label.config(text=f"Sending {file_name}... {progress:.1f}%")
                    
                    time.sleep(0.1)
                    self.text_area.insert(tk.END, f"File sent: {file_name}\n")
                    
                except socket.error as e:
                    self.text_area.insert(tk.END, f"Connection error while sending file: {e}\n")
                    if isinstance(e, (socket.EBADF, socket.ECONNRESET)):
                        self.reconnect()
                finally:
                    progress_label.destroy()
                    
            except Exception as e:
                self.text_area.insert(tk.END, f"Error preparing file: {e}\n")

    def reconnect(self):
        try:
            self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('51.20.191.169', 55557))
            self.perform_handshake()
            self.text_area.insert(tk.END, "Reconnected to server\n")
        except Exception as e:
            self.text_area.insert(tk.END, f"Failed to reconnect: {e}\n")
            self.on_closing()

    def perform_handshake(self):
        try:
            msg = self.socket.recv(1024).decode('utf-8')
            if msg == 'KEY':
                public_key = self.encryption.get_public_key()
                print(f"Sending Public Key:\n{public_key.decode('utf-8')}")
                self.socket.send(public_key)
            
            msg = self.socket.recv(1024).decode('utf-8')
            if msg == 'NICK':
                self.socket.send(self.nickname.encode('utf-8'))
        except Exception as e:
            raise Exception(f"Handshake failed: {e}")

    def handle_file_reception(self, sender_nickname, file_name, file_size, file_extension=None):
        try:
            downloads_dir = "downloads"
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
                
            file_path = os.path.join(downloads_dir, f"received_{file_name}")
            
            progress_label = tk.Label(self.window, text=f"Receiving {file_name}...")
            progress_label.pack()
            
            bytes_received = 0
            with open(file_path, 'wb') as file:
                remaining = file_size
                while remaining > 0:
                    chunk = self.socket.recv(min(4096, remaining))
                    if not chunk:
                        break
                    file.write(chunk)
                    bytes_received += len(chunk)
                    remaining -= len(chunk)
                    progress = (bytes_received / file_size) * 100
                    progress_label.config(text=f"Receiving {file_name}... {progress:.1f}%")
            
            progress_label.destroy()
            
            if file_extension and file_extension.lower() == '.pdf':
                open_button = tk.Button(
                    self.window, 
                    text=f"Open {file_name}", 
                    command=lambda: self.open_pdf(file_path)
                )
                open_button.pack(pady=5)
                
            self.text_area.insert(tk.END, f"Received file '{file_name}' from {sender_nickname}\n")
            self.text_area.insert(tk.END, f"Saved in: {os.path.abspath(file_path)}\n")
            
        except Exception as e:
            self.text_area.insert(tk.END, f"Error receiving file: {e}\n")

    def open_pdf(self, file_path):
        try:
            if sys.platform.startswith('darwin'):
                subprocess.run(['open', file_path])
            elif sys.platform.startswith('win32'):
                os.startfile(file_path)
            else:
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            self.text_area.insert(tk.END, f"Error opening PDF: {e}\n")

    def connect_to_peer(self, peer_ip, peer_port):
        if not self.udp_socket:
            self.setup_udp_socket()
            
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                init_msg = {
                    'type': 'hole_punch',
                    'nickname': self.nickname,
                    'udp_port': self.local_udp_port
                }
                self.udp_socket.sendto(str(init_msg).encode('utf-8'), (peer_ip, peer_port))
                
                try:
                    data, addr = self.udp_socket.recvfrom(1024)
                    response = data.decode('utf-8')
                    if 'hole_punch_ack' in response:
                        self.peer_connections[addr] = {
                            'ip': addr[0],
                            'port': addr[1],
                            'last_seen': time.time()
                        }
                        threading.Thread(target=self.keep_alive_peer, args=(addr,), daemon=True).start()
                        return True
                except socket.timeout:
                    retry_count += 1
                    continue
                    
            except Exception as e:
                retry_count += 1
                time.sleep(1)
                
        return False

    def keep_alive_peer(self, peer_addr):
        while peer_addr in self.peer_connections and self.running:
            try:
                keep_alive_msg = {'type': 'keep_alive', 'nickname': self.nickname}
                self.udp_socket.sendto(str(keep_alive_msg).encode('utf-8'), peer_addr)
                time.sleep(15)
            except Exception as e:
                if peer_addr in self.peer_connections:
                    del self.peer_connections[peer_addr]
                break

    def handle_udp_messages(self):
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                
                if 'hole_punch' in message:
                    ack_msg = {'type': 'hole_punch_ack', 'nickname': self.nickname}
                    self.udp_socket.sendto(str(ack_msg).encode('utf-8'), addr)
                    
                elif 'keep_alive' in message:
                    if addr in self.peer_connections:
                        self.peer_connections[addr]['last_seen'] = time.time()
                        
            except socket.timeout:
                continue
            except Exception:
                continue


    def receive(self):
        while self.running:
            try:
                message = self.socket.recv(1024)
                try:
                    cmd = message.decode('utf-8')

                    if cmd == 'KEY':
                        public_key = self.encryption.get_public_key()
                        self.socket.send(public_key)
                        print(f"Sending Public Key:\n{public_key.decode('utf-8')}")

                    elif cmd == 'NICK':
                        self.socket.send(self.nickname.encode('utf-8'))

                    elif cmd.startswith('FILE:'):
                        try:
                            _, sender_nickname, file_name, file_size, file_extension = cmd.split(':')
                            self.handle_file_reception(sender_nickname, file_name, int(file_size), file_extension)
                        except Exception:
                            pass

                    elif cmd.startswith('PEER_INFO:'):
                        try:
                            _, peer_ip, peer_port = cmd.split(':')
                            peer_port = int(peer_port)
                            if self.connect_to_peer(peer_ip, peer_port):
                                self.text_area.insert(tk.END, f"Connected to peer {peer_ip}:{peer_port}\n")
                            else:
                                self.text_area.insert(tk.END, f"Failed to connect to peer {peer_ip}:{peer_port}\n")
                        except ValueError:
                            pass

                    elif cmd.startswith('GROUP_INFO:'):
                        try:
                            _, group_name, status = cmd.split(':')
                            if status == 'created' or status == 'joined':
                                if group_name not in self.groups:
                                    self.groups[group_name] = {"members": set()}
                                self.update_group_menu()
                                self.text_area.insert(tk.END, f"Successfully {status} group {group_name}\n")
                            self.text_area.see(tk.END)
                        except Exception:
                            pass

                    elif cmd.startswith('GROUP_MEMBERS:'):
                        try:
                            _, group_name, members = cmd.split(':')
                            if group_name in self.groups:
                                self.groups[group_name]["members"] = set(members.split(','))
                                self.text_area.insert(tk.END, f"Group {group_name} members: {members}\n")
                            self.text_area.see(tk.END)
                        except Exception:
                            pass

                    elif cmd.startswith('GROUP_MSG:'):
                        try:
                            _, group_name, message = cmd.split(':', 2)
                            current_group = self.group_var.get()
                            
                            if current_group == group_name:
                                if message.startswith(f"{self.nickname}: "):
                                    content = message[len(f"{self.nickname}: "):]
                                    self.text_area.insert(tk.END, f"[{group_name}] You: {content}\n")
                                else:
                                    self.text_area.insert(tk.END, f"[{group_name}] {message}\n")
                            self.text_area.see(tk.END)
                        except Exception:
                            pass

                    elif cmd.startswith('GROUP_UPDATE:'):
                        try:
                            _, group_name, update_msg = cmd.split(':')
                            self.text_area.insert(tk.END, f"[{group_name}] {update_msg}\n")
                            self.text_area.see(tk.END)
                        except Exception:
                            pass

                    elif cmd.startswith('VOICE:'):
                        try:
                            _, sender_nickname, audio_size = cmd.split(':')
                            self.handle_voice_message(sender_nickname, int(audio_size))
                        except Exception:
                            pass

                    else:
                        try:
                            current_group = self.group_var.get()
                            if current_group == "Global":
                                if not cmd.startswith(f"{self.nickname}: "):
                                    try:
                                        decrypted = self.encryption.decrypt(message)
                                        self.text_area.insert(tk.END, f"{decrypted}\n")
                                    except Exception:
                                        self.text_area.insert(tk.END, f"{cmd}\n")
                                self.text_area.see(tk.END)
                        except Exception:
                            pass

                except UnicodeDecodeError:
                    pass
                
                except Exception:
                    pass

            except Exception:
                if self.running:
                    break

            self.text_area.see(tk.END)

    def send_message(self):
        message = self.input_area.get().strip()
        if message:
            try:
                current_group = self.group_var.get()
                
                if current_group == "Global":
                    formatted_message = f"{self.nickname}: {message}"
                    self.socket.send(formatted_message.encode('utf-8'))
                    self.text_area.insert(tk.END, f"You: {message}\n")
                else:
                    self.socket.send(f"GROUP_MSG:{current_group}:{message}".encode('utf-8'))
                
                self.input_area.delete(0, tk.END)
                self.text_area.see(tk.END)
                
            except Exception:
                self.on_closing()

    def initiate_discovery(self):
        target_nickname = self.discover_input.get().strip()
        if target_nickname:
            try:
                discover_msg = {
                    'type': 'discover',
                    'target': target_nickname,
                    'nickname': self.nickname
                }
                self.socket.send(f"DISCOVER:{target_nickname}".encode('utf-8'))
                self.discover_input.delete(0, tk.END)
            except Exception:
                self.text_area.insert(tk.END, "Failed to initiate discovery.\n")

    def on_closing(self):
        self.running = False
        if self.socket:
            self.socket.close()
        if self.udp_socket:
            self.udp_socket.close()
        self.window.destroy()

    def start(self):
        receive_thread = threading.Thread(target=self.receive)
        udp_thread = threading.Thread(target=self.handle_udp_messages)
        receive_thread.daemon = True
        udp_thread.daemon = True
        receive_thread.start()
        udp_thread.start()
        self.window.mainloop()

    def create_group(self):
        group_name = self.group_name_entry.get().strip()
        if group_name:
            self.socket.send(f"GROUP_CREATE:{group_name}:".encode('utf-8'))
            self.group_name_entry.delete(0, tk.END)

    def join_group(self):
        group_name = self.group_name_entry.get().strip()
        if group_name:
            self.socket.send(f"GROUP_JOIN:{group_name}:".encode('utf-8'))
            self.group_name_entry.delete(0, tk.END)

    def update_group_menu(self):
        menu = self.group_menu["menu"]
        menu.delete(0, "end")
        for group in self.groups.keys():
            menu.add_command(label=group, 
                            command=lambda g=group: self.group_var.set(g))

    def setup_voice_chat(self):
        self.voice_recorder = VoiceRecorder()
        self.voice_player = VoicePlayer()
        
        self.voice_frame = tk.Frame(self.window)
        self.voice_frame.pack(fill='x', padx=10)
        
        self.record_button = tk.Button(
            self.voice_frame,
            text="🎤 Record",
            command=self.toggle_recording
        )
        self.record_button.pack(side='left', pady=5)
        
        self.recording_label = tk.Label(self.voice_frame, text="")
        self.recording_label.pack(side='left', pady=5, padx=5)
        
        self.is_recording = False
        
    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_button.config(text="⏹ Stop")
            self.recording_label.config(text="Recording...")
            self.voice_recorder.start_recording()
        else:
            self.is_recording = False
            self.record_button.config(text="🎤 Record")
            self.recording_label.config(text="")
            
            audio_data = self.voice_recorder.stop_recording()
            self.send_voice_message(audio_data)
            
    def send_voice_message(self, audio_data):
        try:
            header = f"VOICE:{self.nickname}:{len(audio_data)}\n"
            self.socket.send(header.encode('utf-8'))
            
            time.sleep(0.1)
            
            self.socket.sendall(audio_data)
            
            play_button = tk.Button(
                self.text_area,
                text="▶️ Play",
                command=lambda data=audio_data: self.voice_player.play_audio(data)
            )
            
            self.text_area.insert(tk.END, "\nYou sent a voice message: ")
            self.text_area.window_create(tk.END, window=play_button)
            self.text_area.insert(tk.END, "\n")
            self.text_area.see(tk.END)
            
        except Exception as e:
            self.text_area.insert(tk.END, f"Error sending voice message: {e}\n")
            
    def handle_voice_message(self, sender_nickname, audio_size):
        try:
            progress_label = tk.Label(self.window, text="Receiving voice message...")
            progress_label.pack()
            
            audio_data = b''
            remaining = audio_size
            
            while remaining > 0:
                chunk = self.socket.recv(min(8192, remaining))
                if not chunk:
                    break
                audio_data += chunk
                remaining -= len(chunk)
                
                progress = ((audio_size - remaining) / audio_size) * 100
                progress_label.config(text=f"Receiving voice message... {progress:.1f}%")
                
            progress_label.destroy()
            
            play_button = tk.Button(
                self.text_area,
                text="▶️ Play",
                command=lambda: self.voice_player.play_audio(audio_data)
            )
            
            self.text_area.insert(tk.END, f"\n{sender_nickname} sent a voice message: ")
            self.text_area.window_create(tk.END, window=play_button)
            self.text_area.insert(tk.END, "\n")
            self.text_area.see(tk.END)
            
        except Exception as e:
            self.text_area.insert(tk.END, f"Error receiving voice message: {e}\n")

if __name__ == "__main__":
    client = ChatClient()
                        