import sqlite3
import os
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="rssx.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_login INTEGER
            )
            ''')
            
            # Create posts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                signature TEXT NOT NULL
            )
            ''')
            
            # Create servers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                url TEXT PRIMARY KEY,
                last_sync INTEGER
            )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
            # Import existing data if available
            self._import_existing_data()
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def _import_existing_data(self):
        """Import existing data from JSON files"""
        # Import users
        if os.path.exists("users.json"):
            try:
                with open("users.json", "r") as f:
                    users = json.load(f)
                    
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for username, password in users.items():
                    cursor.execute(
                        "INSERT OR IGNORE INTO users (username, password, created_at) VALUES (?, ?, ?)",
                        (username, password, int(time.time()))
                    )
                
                conn.commit()
                conn.close()
                logger.info("Imported existing users data")
            except Exception as e:
                logger.error(f"Error importing users data: {str(e)}")
        
        # Import servers
        if os.path.exists("servers.json"):
            try:
                with open("servers.json", "r") as f:
                    servers = json.load(f)
                    
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for server_url in servers:
                    cursor.execute(
                        "INSERT OR IGNORE INTO servers (url, last_sync) VALUES (?, ?)",
                        (server_url, int(time.time()))
                    )
                
                conn.commit()
                conn.close()
                logger.info("Imported existing servers data")
            except Exception as e:
                logger.error(f"Error importing servers data: {str(e)}")
        
        # Import posts
        posts_dir = Path("posts")
        if posts_dir.exists() and posts_dir.is_dir():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for post_file in posts_dir.glob("*.rssx"):
                    with open(post_file, "r") as f:
                        lines = f.readlines()
                        
                    post_data = {}
                    for line in lines:
                        if ": " in line:
                            key, value = line.split(": ", 1)
                            post_data[key.strip()] = value.strip()
                    
                    # Extract post data
                    post_id = post_data.get("ID", str(int(time.time())))
                    author = post_data.get("Author", "unknown")
                    timestamp = post_data.get("Timestamp", str(int(time.time())))
                    content = post_data.get("Content", "")
                    signature = post_data.get("Signature", "")
                    
                    cursor.execute(
                        "INSERT OR IGNORE INTO posts (id, author, content, timestamp, signature) VALUES (?, ?, ?, ?, ?)",
                        (post_id, author, content, timestamp, signature)
                    )
                
                conn.commit()
                conn.close()
                logger.info("Imported existing posts data")
            except Exception as e:
                logger.error(f"Error importing posts data: {str(e)}")
    
    def get_user(self, username):
        """Get user by username"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return {"username": user[0], "password": user[1]}
            return None
        except sqlite3.Error as e:
            logger.error(f"Database error in get_user: {str(e)}")
            return None
    
    def save_user(self, username, password):
        """Save a new user or update existing user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR REPLACE INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, password, int(time.time()))
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in save_user: {str(e)}")
            return False
    
    def update_login_time(self, username):
        """Update last login time for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE username = ?",
                (int(time.time()), username)
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in update_login_time: {str(e)}")
            return False
    
    def save_post(self, post_data):
        """Save a new post"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            post_id = post_data.get("id", str(int(time.time())))
            
            cursor.execute(
                "INSERT INTO posts (id, author, content, timestamp, signature) VALUES (?, ?, ?, ?, ?)",
                (
                    post_id,
                    post_data["author"],
                    post_data["content"],
                    post_data["timestamp"],
                    post_data["signature"]
                )
            )
            
            conn.commit()
            conn.close()
            return post_id
        except sqlite3.Error as e:
            logger.error(f"Database error in save_post: {str(e)}")
            return None
    
    def get_all_posts(self):
        """Get all posts"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM posts ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            
            posts = []
            for row in rows:
                post_content = f"ID: {row['id']}\nAuthor: {row['author']}\nTimestamp: {row['timestamp']}\nContent: {row['content']}\nSignature: {row['signature']}"
                posts.append(post_content)
            
            conn.close()
            return posts
        except sqlite3.Error as e:
            logger.error(f"Database error in get_all_posts: {str(e)}")
            return []
    
    def get_post_by_id(self, post_id):
        """Get a specific post by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            
            if row:
                post_content = f"ID: {row['id']}\nAuthor: {row['author']}\nTimestamp: {row['timestamp']}\nContent: {row['content']}\nSignature: {row['signature']}"
                return post_content
            
            conn.close()
            return None
        except sqlite3.Error as e:
            logger.error(f"Database error in get_post_by_id: {str(e)}")
            return None
    
    def get_all_servers(self):
        """Get all connected servers"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT url FROM servers")
            rows = cursor.fetchall()
            
            servers = [row[0] for row in rows]
            
            conn.close()
            return servers
        except sqlite3.Error as e:
            logger.error(f"Database error in get_all_servers: {str(e)}")
            return []
    
    def add_server(self, server_url):
        """Add a new server connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR IGNORE INTO servers (url, last_sync) VALUES (?, ?)",
                (server_url, int(time.time()))
            )
            
            conn.commit()
            result = cursor.rowcount > 0
            conn.close()
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error in add_server: {str(e)}")
            return False