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
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_login INTEGER,
                popularity INTEGER DEFAULT 0
            )
            """
            )

            # Create posts table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                signature TEXT NOT NULL,
                upvotes INTEGER DEFAULT 0,
                downvotes INTEGER DEFAULT 0,
                spam INTEGER DEFAULT 0
            )
            """
            )

            # Create servers table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS servers (
                url TEXT PRIMARY KEY,
                last_sync INTEGER
            )
            """
            )

            # Create votes table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                username TEXT NOT NULL,
                vote_type TEXT NOT NULL CHECK(vote_type IN ('upvote', 'downvote')),
                UNIQUE(post_id, username)
            )
            """
            )

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
                    # If password is a list or dict, serialize to JSON string
                    if isinstance(password, (list, dict)):
                        password = json.dumps(password)
                    cursor.execute(
                        "INSERT OR IGNORE INTO users (username, password, created_at) VALUES (?, ?, ?)",
                        (username, password, int(time.time())),
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
                        (server_url, int(time.time())),
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
                        (post_id, author, content, timestamp, signature),
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
            cursor.execute(
                "SELECT username, password FROM users WHERE username = ?", (username,)
            )
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
                (username, password, int(time.time())),
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
                (int(time.time()), username),
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in update_login_time: {str(e)}")
            return False

    def save_post(self, post_data):
        """Save a new post, supporting federated_from for federated posts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Add federated_from column if not present
            try:
                cursor.execute("ALTER TABLE posts ADD COLUMN federated_from TEXT")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    logger.error(f"Error adding federated_from column: {str(e)}")

            post_id = post_data.get("id", str(int(time.time())))
            author = post_data["author"]
            content = post_data["content"]
            timestamp = post_data["timestamp"]
            signature = post_data["signature"]
            federated_from = post_data.get("federated_from")

            if federated_from:
                cursor.execute(
                    "INSERT INTO posts (id, author, content, timestamp, signature, federated_from) VALUES (?, ?, ?, ?, ?, ?)",
                    (post_id, author, content, timestamp, signature, federated_from),
                )
            else:
                cursor.execute(
                    "INSERT INTO posts (id, author, content, timestamp, signature) VALUES (?, ?, ?, ?, ?)",
                    (post_id, author, content, timestamp, signature),
                )

            conn.commit()
            conn.close()
            return post_id
        except sqlite3.Error as e:
            logger.error(f"Database error in save_post: {str(e)}")
            return None

    def get_all_posts(self):
        """Get all posts as a list of dicts, sorted by author popularity and post upvotes"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Join posts with users to get author popularity
            cursor.execute(
                """
                SELECT posts.*, users.popularity as author_popularity
                FROM posts
                LEFT JOIN users ON posts.author = users.username
                ORDER BY author_popularity DESC, posts.upvotes DESC, posts.timestamp DESC
            """
            )
            rows = cursor.fetchall()
            posts = []
            for row in rows:
                post = dict(row)
                post.pop("author_popularity", None)  # Remove if not needed in output
                posts.append(post)
            conn.close()
            return posts
        except sqlite3.Error as e:
            logger.error(f"Database error in get_all_posts: {str(e)}")
            return []

    def get_post_by_id(self, post_id):
        """Get a specific post by ID and return as a dict"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
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
                (server_url, int(time.time())),
            )

            conn.commit()
            result = cursor.rowcount > 0
            conn.close()
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error in add_server: {str(e)}")
            return False

    def save_comment(self, comment_data):
        """Save a new comment to the database and return its ID. Supports federated_from for federated comments."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Ensure the comments table exists and has federated_from column
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    federated_from TEXT
                )
            """
            )
            # Try to add federated_from column if not present
            try:
                cursor.execute("ALTER TABLE comments ADD COLUMN federated_from TEXT")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    logger.error(f"Error adding federated_from column to comments: {str(e)}")

            federated_from = comment_data.get("federated_from")
            if federated_from:
                cursor.execute(
                    "INSERT INTO comments (author, timestamp, content, post_id, signature, federated_from) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        comment_data["author"],
                        comment_data["timestamp"],
                        comment_data["content"],
                        comment_data["post_id"],
                        comment_data["signature"],
                        federated_from,
                    ),
                )
            else:
                cursor.execute(
                    "INSERT INTO comments (author, timestamp, content, post_id, signature) VALUES (?, ?, ?, ?, ?)",
                    (
                        comment_data["author"],
                        comment_data["timestamp"],
                        comment_data["content"],
                        comment_data["post_id"],
                        comment_data["signature"],
                    ),
                )
            conn.commit()
            comment_id = cursor.lastrowid
            conn.close()
            return comment_id
        except sqlite3.Error as e:
            logger.error(f"Database error in save_comment: {str(e)}")
            return None

    def get_comments_for_post(self, post_id):
        """Get all comments for a given post_id, sorted by timestamp ascending"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY timestamp ASC", (post_id,))
            rows = cursor.fetchall()
            comments = [dict(row) for row in rows]
            conn.close()
            return comments
        except sqlite3.Error as e:
            logger.error(f"Database error in get_comments_for_post: {str(e)}")
            return []

    def update_post(self, post_id, new_content):
        """Update the content of an existing post"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id)
            )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except sqlite3.Error as e:
            logger.error(f"Database error in update_post: {str(e)}")
            return False

    def upvote_post(self, post_id, username):
        """Allow a user to upvote a post only once"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Check if user already voted
            cursor.execute(
                "SELECT vote_type FROM votes WHERE post_id = ? AND username = ?",
                (post_id, username),
            )
            row = cursor.fetchone()
            if row:
                if row[0] == "upvote":
                    conn.close()
                    return False  # Already upvoted
                elif row[0] == "downvote":
                    # Change downvote to upvote
                    cursor.execute(
                        "UPDATE votes SET vote_type = 'upvote' WHERE post_id = ? AND username = ?",
                        (post_id, username),
                    )
                    cursor.execute(
                        "UPDATE posts SET upvotes = upvotes + 1, downvotes = downvotes - 1 WHERE id = ?",
                        (post_id,),
                    )
                else:
                    conn.close()
                    return False
            else:
                # New upvote
                cursor.execute(
                    "INSERT INTO votes (post_id, username, vote_type) VALUES (?, ?, 'upvote')",
                    (post_id, username),
                )
                cursor.execute(
                    "UPDATE posts SET upvotes = upvotes + 1 WHERE id = ?", (post_id,)
                )
            # Update author popularity
            cursor.execute("SELECT author FROM posts WHERE id = ?", (post_id,))
            author = cursor.fetchone()
            if author:
                cursor.execute(
                    "UPDATE users SET popularity = popularity + 1 WHERE username = ?",
                    (author[0],),
                )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in upvote_post: {str(e)}")
            return False

    def downvote_post(self, post_id, username):
        """Allow a user to downvote a post only once"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Check if user already voted
            cursor.execute(
                "SELECT vote_type FROM votes WHERE post_id = ? AND username = ?",
                (post_id, username),
            )
            row = cursor.fetchone()
            if row:
                if row[0] == "downvote":
                    conn.close()
                    return False  # Already downvoted
                elif row[0] == "upvote":
                    # Change upvote to downvote
                    cursor.execute(
                        "UPDATE votes SET vote_type = 'downvote' WHERE post_id = ? AND username = ?",
                        (post_id, username),
                    )
                    cursor.execute(
                        "UPDATE posts SET downvotes = downvotes + 1, upvotes = upvotes - 1 WHERE id = ?",
                        (post_id,),
                    )
                else:
                    conn.close()
                    return False
            else:
                # New downvote
                cursor.execute(
                    "INSERT INTO votes (post_id, username, vote_type) VALUES (?, ?, 'downvote')",
                    (post_id, username),
                )
                cursor.execute(
                    "UPDATE posts SET downvotes = downvotes + 1 WHERE id = ?", (post_id,),
                )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in downvote_post: {str(e)}")
            return False

    def mark_spam_column(self):
        """Ensure the posts table has a 'spam' column for decentralized spam marking."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE posts ADD COLUMN spam INTEGER DEFAULT 0")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            # Column already exists
            if "duplicate column name" not in str(e):
                logger.error(f"Error adding spam column: {str(e)}")

    def remove_spam_posts(self, blacklist=None):
        """Mark posts as spam (decentralized): more downvotes than upvotes, or containing blacklisted words."""
        self.mark_spam_column()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Mark posts with more downvotes than upvotes as spam
            cursor.execute("UPDATE posts SET spam = 1 WHERE downvotes > upvotes")
            # Mark posts containing blacklisted words as spam
            if blacklist:
                for word in blacklist:
                    cursor.execute(
                        "UPDATE posts SET spam = 1 WHERE content LIKE ?", (f"%{word}%",)
                    )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error in remove_spam_posts: {str(e)}")
            return False


if __name__ == "__main__":
    import argparse
    from datetime import datetime
    import os
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(
        description="Initialize or reset the RSSx database."
    )
    parser.add_argument("--init", action="store_true", help="Initialize the database")
    parser.add_argument(
        "--reset", action="store_true", help="Backup and reinitialize the database"
    )
    args = parser.parse_args()

    db_file = "rssx.db"
    backup_dir = "db_backups"

    if args.reset:
        if os.path.exists(db_file):
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)

            # Get local time with timezone info
            local_tz = datetime.now().astimezone().tzinfo
            now = datetime.now(local_tz)
            timestamp = now.strftime("%d%m%Y_%H%M%S")
            timezone_abbr = now.strftime("%Z")  # e.g., IST, UTC

            backup_filename = f"rssx_{timestamp}_{timezone_abbr}.db"
            backup_path = os.path.join(backup_dir, backup_filename)

            os.rename(db_file, backup_path)
            print(f"Existing database backed up as {backup_path}")
        else:
            print("No existing database found. Creating a fresh database.")

    # Initialize the new (or reset) DB
    if args.init or args.reset:
        db = Database()
        print("Database initialized.")
    else:
        print("Use --init to initialize or --reset to backup and reset the database.")
