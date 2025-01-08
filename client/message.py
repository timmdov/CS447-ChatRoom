# message.py
class MessageHandler:
    def __init__(self):
        self.message_queue = []
        
    def format_message(self, message, sender):
        return f"{sender}: {message}"

    def process_received(self, message, encryption):
        if message.startswith('MESSAGE'):
            return encryption.decrypt(message[7:])