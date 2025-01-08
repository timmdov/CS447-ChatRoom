# utils.py
"""
    Provides utility functions for the chat system that are commonly used across the application.
"""
class Utils:

    """ Ensures the nickname is alphanumeric and no longer than 32 characters. """
    @staticmethod
    def validate_nickname(nickname):
        return nickname.isalnum() and len(nickname) <= 32

    """ Formats a message with the sender’s name. """
    @staticmethod
    def format_message(message, sender):
        return f"{sender}: {message}"

    """ Logs an error to the console and closes the client connection (if provided). """
    @staticmethod
    def handle_error(error, client=None):
        print(f"Error: {error}")
        if client:
            client.close()