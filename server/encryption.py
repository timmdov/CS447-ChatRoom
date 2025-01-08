import rsa

class ServerEncryption:
    """
    Server-side encryption handling for managing client keys and verifying encryption.
    Facilitates secure key exchange between clients.
    """
    
    def __init__(self):
        """Initialize server encryption state"""
        self.public_key = None

    @staticmethod
    def load_public_key(key_data):
        """
        Load a public key from PEM format
        
        Args:
            key_data: Public key in PEM format (bytes)
            
        Returns:
            rsa.PublicKey: Loaded public key object
        """
        try:
            return rsa.PublicKey.load_pkcs1(key_data, format='PEM')
        except Exception as e:
            print(f"Error loading public key: {e}")
            return None

    @staticmethod
    def verify_key(public_key):
        """
        Verify a public key by attempting encryption
        
        Args:
            public_key: RSA public key to verify
            
        Returns:
            bool: True if key is valid, False otherwise
        """
        if not public_key:
            return False
            
        try:
            test_message = rsa.encrypt(b'test', public_key)
            return True
        except:
            return False

    def get_public_key(self):
        """
        Get server's public key in PEM format
        
        Returns:
            bytes: Public key in PEM format
        """
        if self.public_key:
            return self.public_key.save_pkcs1(format='PEM')
        return None