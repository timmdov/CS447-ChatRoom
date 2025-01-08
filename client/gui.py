# gui.py
import tkinter as tk
from tkinter import scrolledtext

class ChatGUI:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.setup_gui()

    def setup_gui(self):
        self.root.title("Encrypted Chat")
        self.chat_area = scrolledtext.ScrolledText(self.root)
        self.msg_entry = tk.Entry(self.root)
        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)


        self.discover_label = tk.Label(self.window, text="Discover Peer:")
        self.discover_label.pack(pady=5)

        self.discover_input = tk.Entry(self.window)
        self.discover_input.pack(fill='x', padx=10, pady=5)

        self.discover_button = tk.Button(self.window, text="Discover", command=self.initiate_discovery)
        self.discover_button.pack(pady=5)