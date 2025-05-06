import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_file="config.json"):
        """Initialize configuration with defaults and load from file if available"""
        self.config_file = config_file
        self.config = {
            # Server settings
            "HOST": "0.0.0.0",
            "PORT": 5000,
            "DEBUG": False,
            
            # Security settings
            "JWT_SECRET_KEY": os.environ.get("RSSX_JWT_SECRET", "your_secret_key"),
            "PUBLIC_KEY_FILE": "rsa_public.pem",
            "PRIVATE_KEY_FILE": "rsa_private.pem",
            "TOKEN_EXPIRY_HOURS": 24,
            
            # Database settings
            "DB_PATH": "rssx.db",
            
            # Path settings
            "POSTS_DIRECTORY": "posts",
            "USERS_FILE": "users.json",
            "SERVERS_FILE": "servers.json",
            
            # Logging settings
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "rssx.log",
            
            # UI settings
            "ENABLE_WEB_UI": True,
            "ENABLE_TUI": True,
            "ENABLE_TKINTER_UI": True,
            "WEB_TEMPLATE_DIR": "rssx/templates",
            "WEB_STATIC_DIR": "rssx/static",
            
            # Client settings
            "DEFAULT_SERVER": "http://127.0.0.1:5000"
        }
        
        # Load configuration from file if it exists
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update default config with loaded values
                    self.config.update(loaded_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            except json.JSONDecodeError:
                logger.error(f"Error parsing configuration file {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value by key"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value and save to file"""
        self.config[key] = value
        return self.save_config()
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.get("POSTS_DIRECTORY"),
            "rssx/templates",
            "rssx/static",
            "rssx/static/css",
            "rssx/static/js",
            Path(self.get("LOG_FILE")).parent
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
        
        return True