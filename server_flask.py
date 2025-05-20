import argparse
import logging
from flask import Flask, session, render_template
from rssx.utils.config import Config
from rssx.utils.logging_config import setup_logging
from rssx.database.db import Database
from rssx.security.crypto import Security
from rssx.ui.web.web_controller import WebUI
from flask import Blueprint, request, jsonify
import time
from collections import defaultdict, deque
from flask_cors import CORS

logger = logging.getLogger(__name__)

# In-memory throttling and spam filter state
THROTTLE_LIMIT = 5  # max requests per user per minute
THROTTLE_WINDOW = 60  # seconds
BLACKLISTED_WORDS = []
user_post_times = defaultdict(lambda: deque(maxlen=THROTTLE_LIMIT))
user_comment_times = defaultdict(lambda: deque(maxlen=THROTTLE_LIMIT))
user_last_post_content = {}
user_last_comment_content = {}

class RSSXApi:
    def __init__(self, database, security):
        """Initialize the API with database and security instances"""
        self.db = database
        self.security = security
        self.api = Blueprint("api", __name__)
        self.register_routes()

    def register_routes(self):
        """Register all API routes"""
        # User authentication routes
        self.api.route("/register", methods=["POST"])(self.register)
        self.api.route("/login", methods=["POST"])(self.login)

        # Post management routes
        self.api.route("/post", methods=["POST"])(self.create_post)
        self.api.route("/feed", methods=["GET"])(self.get_feed)
        self.api.route("/post/<post_id>", methods=["GET"])(self.get_post)
        self.api.route("/upvote", methods=["POST"])(self.upvote_post)
        self.api.route("/downvote", methods=["POST"])(self.downvote_post)

        # Server management routes
        self.api.route("/list_servers", methods=["GET"])(self.list_servers)
        self.api.route("/add_server", methods=["POST"])(self.add_server)
        self.api.route("/register_ip", methods=["POST"])(self.register_ip)

        # User profile routes
        self.api.route("/profile", methods=["GET"])(self.get_profile)

        # Health check route
        self.api.route("/health", methods=["GET"])(self.health_check)
        # Comment to post route
        self.api.route("/comment", methods=["POST"])(self.create_comment)

        # Public key route
        self.api.route('/public_key', methods=['GET'])(self.get_public_key)

        # Federated post route
        self.api.route('/receive_post', methods=['POST'])(self.receive_post)

        # Federated comment receive endpoint
        self.api.route('/receive_comment', methods=['POST'])(self.receive_comment)

        # Federated vote receive endpoint
        self.api.route('/receive_vote', methods=['POST'])(self.receive_vote)

    def receive_comment(self):
        """Receive a federated comment encrypted for this server"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        # Required fields: author, timestamp, content (encrypted), signature, post_id, federated_from
        author = data.get("author")
        timestamp = data.get("timestamp")
        content = data.get("content")
        signature = data.get("signature")
        post_id = data.get("post_id")
        federated_from = data.get("federated_from")
        if not all([author, timestamp, content, signature, post_id, federated_from]):
            return jsonify({"error": "Missing required fields"}), 400

        # Check if this post is local or federated
        post = self.db.get_post_by_id(post_id)
        if post and post.get("federated_from") and post["federated_from"] != federated_from:
            # This is a federated post, not the origin. Forward to the origin server.
            import requests as pyrequests
            origin_server = post["federated_from"]
            # Forward the comment to the origin server's /api/receive_comment
            try:
                url = origin_server
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "http://" + url
                res = pyrequests.post(url + "/api/receive_comment", json=data, timeout=5)
                if res.ok:
                    return jsonify({"message": "Comment forwarded to origin server"}), 200
                else:
                    return jsonify({"error": "Failed to forward comment to origin server"}), 502
            except Exception as e:
                logger.error(f"Error forwarding federated comment: {e}")
                return jsonify({"error": "Network error forwarding comment to origin server"}), 502

        # Decrypt the content with the server's private key (if encrypted)
        try:
            from base64 import b64decode
            logger.info(f"Attempting to decrypt federated comment from {federated_from} with content: {content[:40]}...")
            decrypted_bytes = self.security.private_key.decrypt(
                b64decode(content),
                self.security._get_rsa_padding()
            )
            plaintext_content = decrypted_bytes.decode('utf-8')
            logger.info(f"Decryption successful. Plaintext: {plaintext_content[:40]}...")
        except Exception as e:
            logger.error(f"Failed to decrypt federated comment: {e}")
            return jsonify({"error": "Failed to decrypt federated comment"}), 400
        # Save as a comment, mark as federated
        comment_data = {
            "author": author,
            "timestamp": timestamp,
            "content": plaintext_content,
            "post_id": post_id,
            "signature": signature,
            "federated_from": federated_from
        }
        comment_id = self.db.save_comment(comment_data)
        if not comment_id:
            logger.error(f"Failed to save federated comment from {federated_from}")
            return jsonify({"error": "Failed to save federated comment"}), 500
        logger.info(f"Federated comment received from {federated_from} for post {post_id}")
        return jsonify({"message": "Federated comment received", "comment_id": comment_id}), 201

    def receive_vote(self):
        """Receive a federated upvote/downvote for a post from another server"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        post_id = data.get("post_id")
        vote_type = data.get("vote_type")  # 'upvote' or 'downvote'
        voter = data.get("voter")  # user@server
        if not all([post_id, vote_type, voter]):
            return jsonify({"error": "Missing required fields"}), 400
        # Check if this post is local or federated
        post = self.db.get_post_by_id(post_id)
        if post and post.get("federated_from") and post["federated_from"] != voter.split('@')[-1]:
            # This is a federated post, not the origin. Forward to the origin server.
            import requests as pyrequests
            origin_server = post["federated_from"]
            try:
                url = origin_server
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "http://" + url
                res = pyrequests.post(url + "/api/receive_vote", json=data, timeout=5)
                if res.ok:
                    return jsonify({"message": "Vote forwarded to origin server"}), 200
                else:
                    return jsonify({"error": "Failed to forward vote to origin server"}), 502
            except Exception as e:
                logger.error(f"Error forwarding federated vote: {e}")
                return jsonify({"error": "Network error forwarding vote to origin server"}), 502
        # Use voter as username for uniqueness
        if vote_type == 'upvote':
            success = self.db.upvote_post(post_id, voter)
        elif vote_type == 'downvote':
            success = self.db.downvote_post(post_id, voter)
        else:
            return jsonify({"error": "Invalid vote_type"}), 400
        if success:
            return jsonify({"message": f"{vote_type} registered"}), 200
        else:
            return jsonify({"error": f"Failed to register {vote_type}"}), 400

    def create_comment(self):
        """Create a new comment on a post with spam filter and throttling"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get("username")

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        content = data.get("content")
        post_id = data.get("post_id")
        federated_from = data.get("federated_from")
        if not content or not post_id:
            return jsonify({"error": "Content and post_id are required"}), 400

        # Throttling: block if too many comments in window
        now = time.time()
        times = user_comment_times[username]
        times.append(now)
        if len(times) == THROTTLE_LIMIT and now - times[0] < THROTTLE_WINDOW:
            return jsonify({"error": "Too many comments, slow down!"}), 429

        # Block repeated content
        if user_last_comment_content.get(username) == content:
            return jsonify({"error": "Duplicate comment detected"}), 400
        user_last_comment_content[username] = content

        # Spam filter: block blacklisted words
        for word in BLACKLISTED_WORDS:
            if word.lower() in content.lower():
                return jsonify({"error": f"Spam detected: '{word}' is not allowed"}), 400

        # Create comment data
        timestamp = int(time.time())
        comment_data = {
            "author": username,
            "timestamp": timestamp,
            "content": content,
            "post_id": post_id,
        }
        if federated_from:
            comment_data["federated_from"] = federated_from

        # Sign the comment data
        signature_data = f"{comment_data['timestamp']}{comment_data['author']}{comment_data['content']}"
        comment_data["signature"] = self.security.sign_data(signature_data)

        # Save comment to database
        comment_id = self.db.save_comment(comment_data)
        if not comment_id:
            logger.error(f"Failed to save comment for user: {username}")
            return jsonify({"error": "Failed to save comment"}), 500
        logger.info(f"Comment created by {username} with ID: {comment_id} for post {post_id}")
        return jsonify({"message": "Comment created successfully", "comment_id": comment_id}), 201

    def register(self):
        """Register a new user"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # Check if username already exists
        existing_user = self.db.get_user(username)
        if existing_user:
            return jsonify({"error": "Username already taken"}), 409

        # Hash password and save user
        hashed_password = self.security.hash_password(password)
        if self.db.save_user(username, hashed_password):
            logger.info(f"User registered: {username}")
            return jsonify({"message": "User registered successfully"}), 201
        else:
            logger.error(f"Failed to register user: {username}")
            return jsonify({"error": "Failed to register user"}), 500

    def login(self):
        """Login a user and return a JWT token"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # Get user from database
        user = self.db.get_user(username)
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return jsonify({"error": "Invalid credentials"}), 401

        # Verify password
        if not self.security.verify_password(password, user["password"]):
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate JWT token
        token = self.security.generate_jwt(username)
        if not token:
            logger.error(f"Failed to generate token for user: {username}")
            return jsonify({"error": "Failed to generate authentication token"}), 500

        # Store token in session so we can access it in feed.html
        session["token"] = token

        # Update last login time
        self.db.update_login_time(username)

        logger.info(f"User logged in: {username}")
        return jsonify({"token": token}), 200

    def create_post(self):
        """Create a new post with spam filter and throttling"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get("username")

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        content = data.get("content")
        if not content:
            return jsonify({"error": "Content is required"}), 400

        # Throttling: block if too many posts in window
        now = time.time()
        times = user_post_times[username]
        times.append(now)
        if len(times) == THROTTLE_LIMIT and now - times[0] < THROTTLE_WINDOW:
            return jsonify({"error": "Too many posts, slow down!"}), 429

        # Block repeated content
        if user_last_post_content.get(username) == content:
            return jsonify({"error": "Duplicate post detected"}), 400
        user_last_post_content[username] = content

        # Spam filter: block blacklisted words
        for word in BLACKLISTED_WORDS:
            if word.lower() in content.lower():
                return jsonify({"error": f"Spam detected: '{word}' is not allowed"}), 400

        # Create post data
        timestamp = int(time.time())
        post_data = {"author": username, "timestamp": timestamp, "content": content}

        # Sign the post data
        signature_data = (
            f"{post_data['timestamp']}{post_data['author']}{post_data['content']}"
        )
        post_data["signature"] = self.security.sign_data(signature_data)

        # Save post to database
        post_id = self.db.save_post(post_data)
        if not post_id:
            logger.error(f"Failed to save post for user: {username}")
            return jsonify({"error": "Failed to save post"}), 500

        logger.info(f"Post created by {username} with ID: {post_id}")
        return (
            jsonify({"message": "Post created successfully", "post_id": post_id}),
            201,
        )

    def upvote_post(self):
        """Handle upvoting a post (one per user)"""
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get("username")
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        post_id = data.get("post_id")
        if not post_id:
            return jsonify({"error": "post_id is required"}), 400
        success = self.db.upvote_post(post_id, username)
        self.db.remove_spam_posts()  # Update spam status after voting
        if success:
            return jsonify({"message": "Post upvoted successfully"}), 200
        else:
            return (
                jsonify(
                    {"error": "You have already upvoted this post or error occurred"}
                ),
                400,
            )

    def downvote_post(self):
        """Handle downvoting a post (one per user)"""
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get("username")
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        post_id = data.get("post_id")
        if not post_id:
            return jsonify({"error": "post_id is required"}), 400
        success = self.db.downvote_post(post_id, username)
        self.db.remove_spam_posts()  # Update spam status after voting
        if success:
            return jsonify({"message": "Post downvoted successfully"}), 200
        else:
            return (
                jsonify(
                    {"error": "You have already downvoted this post or error occurred"}
                ),
                400,
            )

    def get_feed(self):
        """Get all posts sorted by author popularity and upvotes, including comments"""
        posts = self.db.get_all_posts()
        # Sort posts by author popularity and upvotes
        posts.sort(key=lambda post: (
            self.db.get_user(post['author']).get('popularity', 0),
            post.get('upvotes', 0)
        ), reverse=True)
        # Attach comments to each post
        for post in posts:
            comments = self.db.get_comments_for_post(post['id'])
            # Format timestamp for comments
            for comment in comments:
                comment['timestamp_formatted'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(comment['timestamp']))
            post['comments'] = comments
        return jsonify({"posts": posts}), 200

    def get_post(self, post_id):
        """Get a specific post by ID, including comments"""
        post = self.db.get_post_by_id(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        comments = self.db.get_comments_for_post(post_id)
        for comment in comments:
            comment['timestamp_formatted'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(comment['timestamp']))
        post['comments'] = comments
        return jsonify({"post": post}), 200

    def list_servers(self):
        """List all connected servers"""
        servers = self.db.get_all_servers()
        return jsonify({"connected_servers": servers}), 200

    def add_server(self):
        """Add a new server to the connected servers list"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        server_url = data.get("server_url")
        if not server_url:
            return jsonify({"error": "Missing server_url"}), 400

        # Add server to database
        success = self.db.add_server(server_url)
        if not success:
            return jsonify({"error": "Server already connected or failed to add"}), 400

        logger.info(f"New server added: {server_url}")
        return jsonify({"message": f"Server {server_url} added successfully"}), 201

    def register_ip(self):
        """Register IP address with username (for P2P)"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username")
        if not username:
            return jsonify({"error": "Missing username"}), 400

        # In a real implementation, this would store the IP-username mapping
        # For now, we just acknowledge the request
        client_ip = request.remote_addr
        logger.info(f"IP {client_ip} registered for username: {username}")

        return jsonify({"message": f"IP registered for {username}"}), 200

    def get_profile(self):
        """Get user profile information"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get("username")

        user = self.db.get_user(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Don't return the password hash
        profile = {
            "username": user["username"],
            # You could add more profile fields here
        }

        return jsonify({"profile": profile}), 200

    def health_check(self):
        """Health check endpoint"""
        return jsonify({"status": "ok", "timestamp": int(time.time())}), 200

    def get_public_key(self):
        """Expose the server's public key in PEM format for federation encryption"""
        from cryptography.hazmat.primitives import serialization
        pem = self.security.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        return jsonify({"public_key": pem})

    def receive_post(self):
        """Receive a federated post encrypted for this server"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        # Required fields: author, timestamp, content (encrypted), signature, federated_from
        author = data.get("author")
        timestamp = data.get("timestamp")
        content = data.get("content")
        signature = data.get("signature")
        federated_from = data.get("federated_from")
        if not all([author, timestamp, content, signature, federated_from]):
            return jsonify({"error": "Missing required fields"}), 400
        # Decrypt the content with the server's private key (less secure, not E2E)
        try:
            from base64 import b64decode
            logger.info(f"Attempting to decrypt federated post from {federated_from} with content: {content[:40]}...")
            decrypted_bytes = self.security.private_key.decrypt(
                b64decode(content),
                self.security._get_rsa_padding()
            )
            plaintext_content = decrypted_bytes.decode('utf-8')
            logger.info(f"Decryption successful. Plaintext: {plaintext_content[:40]}...")
        except Exception as e:
            logger.error(f"Failed to decrypt federated post: {e}")
            return jsonify({"error": "Failed to decrypt federated post"}), 400
        # Save as a post, mark as federated (e.g., add a federated_from field or flag)
        post_data = {
            "author": author,
            "timestamp": timestamp,
            "content": plaintext_content,
            "signature": signature,
            "federated_from": federated_from
        }
        post_id = self.db.save_post(post_data)
        if not post_id:
            logger.error(f"Failed to save federated post from {federated_from}")
            return jsonify({"error": "Failed to save federated post"}), 500
        logger.info(f"Federated post received from {federated_from} with ID: {post_id}")
        return jsonify({"message": "Federated post received", "post_id": post_id}), 201


def create_app(config=None):
    """Create and configure the Flask application"""
    if config is None:
        config = Config()

    # Ensure all directories exist
    config.ensure_directories()

    # Set up logging
    logger = setup_logging(config)
    logger.info("Starting RSSX Server")

    # Initialize database
    db = Database(config.get("DB_PATH"))
    logger.info(f"Database initialized at {config.get('DB_PATH')}")

    # Initialize security
    security = Security(config.config)
    logger.info("Security module initialized")

    # Create Flask app
    app = Flask(
        __name__,
        template_folder=config.get("WEB_TEMPLATE_DIR"),
        static_folder=config.get("WEB_STATIC_DIR"),
    )
    CORS(app)
    app.config["SECRET_KEY"] = config.get("JWT_SECRET_KEY")
    app.config["SESSION_TYPE"] = "filesystem"

    # Register index route here, after app is defined
    @app.route("/")
    def index():
        if config.get("ENABLE_WEB_UI"):
            # Render feed.html and supply the JWT token from session (if available)
            return render_template("feed.html", token=session.get("token"))
        else:
            return {
                "status": "ok",
                "message": "RSSX API Server",
                "api_endpoints": [
                    "/api/register",
                    "/api/login",
                    "/api/feed",
                    "/api/post",
                    "/api/list_servers",
                    "/api/add_server",
                    "/api/health",
                ],
            }

    # Initialize API
    api = RSSXApi(db, security)
    app.register_blueprint(api.api, url_prefix="/api")
    logger.info("API registered at /api")

    # Initialize Web UI if enabled
    if config.get("ENABLE_WEB_UI"):
        web_ui = WebUI(db, security, config)
        app.register_blueprint(web_ui.web, url_prefix="/")
        logger.info("Web UI registered at /")
    return app


def run_server(config=None, host="0.0.0.0", port=5000, debug=True):
    """Run the RSSX server"""
    # Create application
    app = create_app(config)  # Only get 'app' here

    # Use command-line values if provided, otherwise use config
    if host:
        config.set("HOST", host)
    if port:
        config.set("PORT", port)
    if debug is not None:
        config.set("DEBUG", debug)
    # Start the server
    app.run(
        host=config.get("HOST"), port=int(config.get("PORT")), debug=config.get("DEBUG")
    )

def run_tkinter_ui(config=None):
    """Run the Tkinter UI client"""
    # Import here to avoid dependency if not used
    try:
        from rssx.ui.tkinter.tkinter_client import launch_tkinter_ui

        # If no config provided, create one
        if config is None:
            config = Config()

        # Launch Tkinter UI
        launch_tkinter_ui(config)
    except ImportError as e:
        print(f"Error importing Tkinter UI: {str(e)}")
        print("Make sure you have tkinter installed or re-install the application.")


def main():
    """Main entry point for the application"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="RSSX Distributed Social Media Platform"
    )
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", help="Host address to bind to")
    parser.add_argument("--port", type=int, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-web-ui", action="store_true", help="Disable web UI")
    parser.add_argument(
        "--client", choices=["tui", "gui", "web"], help="Run a client interface"
    )
    parser.add_argument(
        "--db", help="Path to database file (will be created if it doesn't exist)"
    )

    args = parser.parse_args()

    # Load configuration
    config = Config(args.config if args.config else "config.json")
    if args.db:
        config.set("DB_PATH", args.db)

    # Apply command-line overrides
    if args.no_web_ui:
        config.set("ENABLE_WEB_UI", False)

    if args.client:
        if args.client == "tui":
            # Import and run TUI client
            try:
                from client_tui import menu

                menu()
            except ImportError:
                print("TUI client not available")
        elif args.client == "gui":
            # Run Tkinter UI
            run_tkinter_ui(config)
        elif args.client == "web":
            # Just inform that web UI is accessible via browser
            print(
                f"Web UI available at http://{config.get('HOST')}:{config.get('PORT')}/"
            )
            run_server(config, args.host, args.port, args.debug)
    else:
        # Run the server by default
        run_server(config, args.host, args.port, args.debug)


if __name__ == "__main__":
    main()
