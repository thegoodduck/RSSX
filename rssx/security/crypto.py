import os
import jwt
import bcrypt
import logging
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

class Security:
    def __init__(self, config):
        """Initialize security module with configuration"""
        self.config = config
        self.secret_key = config.get("JWT_SECRET_KEY", "your_secret_key")
        self.private_key = None
        self.public_key = None
        self.load_or_generate_keys()
    
    def load_or_generate_keys(self):
        """Load existing RSA keys or generate new ones"""
        public_key_path = self.config.get("PUBLIC_KEY_FILE", "rsa_public.pem")
        private_key_path = self.config.get("PRIVATE_KEY_FILE", "rsa_private.pem")
        
        try:
            # Try to load existing keys
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                with open(private_key_path, "rb") as key_file:
                    self.private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None
                    )
                
                with open(public_key_path, "rb") as key_file:
                    self.public_key = serialization.load_pem_public_key(
                        key_file.read()
                    )
                
                logger.info("RSA keys loaded successfully")
            else:
                # Generate new keys
                self.generate_rsa_keys(public_key_path, private_key_path)
        except Exception as e:
            logger.error(f"Error loading RSA keys: {str(e)}")
            # If loading fails, generate new keys
            self.generate_rsa_keys(public_key_path, private_key_path)
    
    def generate_rsa_keys(self, public_key_path, private_key_path):
        """Generate new RSA key pair"""
        try:
            # Generate private key
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Get public key
            self.public_key = self.private_key.public_key()
            
            # Save private key
            with open(private_key_path, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save public key
            with open(public_key_path, "wb") as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            logger.info("RSA keys generated successfully")
        except Exception as e:
            logger.error(f"Error generating RSA keys: {str(e)}")
            raise
    
    def hash_password(self, password):
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
    
    def verify_password(self, password, hashed_password):
        """Verify a password against a hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode())
    
    def generate_jwt(self, username, expiry_hours=24):
        """Generate a JWT token for authentication"""
        try:
            expiry = datetime.datetime.now() + datetime.timedelta(hours=expiry_hours)
            payload = {
                "username": username,
                "exp": int(expiry.timestamp()),
                "iat": int(datetime.datetime.now().timestamp())
            }
            return jwt.encode(payload, self.secret_key, algorithm="HS256")
        except Exception as e:
            logger.error(f"Error generating JWT: {str(e)}")
            return None
    
    def verify_jwt(self, token):
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            logger.error(f"Error verifying JWT: {str(e)}")
            return None
    
    def sign_data(self, data):
        """Sign data with the RSA private key"""
        try:
            signature = self.private_key.sign(
                data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature.hex()
        except Exception as e:
            logger.error(f"Error signing data: {str(e)}")
            return None
    
    def verify_signature(self, data, signature, public_key=None):
        """Verify a signature with the RSA public key"""
        try:
            # Use provided public key or the instance's public key
            key_to_use = public_key if public_key else self.public_key
            
            # Convert hex signature back to bytes
            signature_bytes = bytes.fromhex(signature)
            
            # Verify signature
            key_to_use.verify(
                signature_bytes,
                data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            logger.warning("Invalid signature")
            return False
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
    
    def _get_rsa_padding(self):
        """Return the RSA OAEP padding used for encryption/decryption"""
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes
        return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )