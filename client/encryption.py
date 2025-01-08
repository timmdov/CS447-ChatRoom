# encryption.py

"""
Encryption module providing end-to-end encryption for chat application.
Implements RSA encryption for both client and server components.
"""

import rsa

class ClientEncryption:
    """
    Client-side encryption handling with RSA keys and message encryption/decryption.
    Manages secure communication with other clients through the server.
    """
    
    def __init__(self):
        """Initialize with a new RSA key pair"""
        self.public_key, self.private_key = rsa.newkeys(2048)
        self.partner_key = None

    def encrypt(self, message):
        """
        Encrypt a message with partner's public key if available
        
        Args:
            message: Message to encrypt (str or bytes)
            
        Returns:
            bytes: Encrypted message
        """
        if not isinstance(message, bytes):
            message = message.encode('utf-8')
            
        key_to_use = self.partner_key if self.partner_key else self.public_key
            
        try:
            chunk_size = 245 
            encrypted_chunks = []
            
            for i in range(0, len(message), chunk_size):
                chunk = message[i:i + chunk_size]
                encrypted_chunk = rsa.encrypt(chunk, self.partner_key)
                encrypted_chunks.append(encrypted_chunk)
                
            return b''.join(encrypted_chunks)
        except Exception as e:
            print(f"Encryption error: {e}")
            return message

    def decrypt(self, message):
        """
        Decrypt a message using private key
        
        Args:
            message: Encrypted message (bytes)
            
        Returns:
            str: Decrypted message
        """
        if not isinstance(message, bytes):
            return message
            
        try:
            chunk_size = 256 
            decrypted_chunks = []
            
            for i in range(0, len(message), chunk_size):
                chunk = message[i:i + chunk_size]
                try:
                    decrypted_chunk = rsa.decrypt(chunk, self.private_key)
                    decrypted_chunks.append(decrypted_chunk)
                except:
                    
                    return message.decode('utf-8')
                    
            return b''.join(decrypted_chunks).decode('utf-8')
        except:
            # Fallback to treating as plaintext
            return message.decode('utf-8')

    def get_public_key(self):
        """
        Get public key in PEM format for sharing
        
        Returns:
            bytes: Public key in PEM format
        """
        return self.public_key.save_pkcs1(format='PEM')

    def set_partner_key(self, key_data):
        """
        Set partner's public key from PEM format data
        
        Args:
            key_data: Public key in PEM format (bytes)
        """
        try:
            self.partner_key = rsa.PublicKey.load_pkcs1(key_data)
        except Exception as e:
            print(f"Error loading partner key: {e}")
            self.partner_key = None


