import os
import argparse
import logging
import threading
from flask import Flask, session, render_template
from pathlib import Path

# Import our modules
from rssx.utils.config import Config
from rssx.utils.logging_config import setup_logging
from rssx.database.db import Database
from rssx.security.crypto import Security
from rssx.ui.web.web_controller import WebUI
from flask import Blueprint, request, jsonify
import logging
import time
import datetime

logger = logging.getLogger(__name__)

class RSSXApi:
    def __init__(self, database, security):
        """Initialize the API with database and security instances"""
        self.db = database
        self.security = security
        self.api = Blueprint('api', __name__)
        self.register_routes()

    def register_routes(self):
        """Register all API routes"""
        # User authentication routes
        self.api.route('/register', methods=['POST'])(self.register)
        self.api.route('/login', methods=['POST'])(self.login)

        # Post management routes
        self.api.route('/post', methods=['POST'])(self.create_post)
        self.api.route('/feed', methods=['GET'])(self.get_feed)
        self.api.route('/post/<post_id>', methods=['GET'])(self.get_post)

        # Server management routes
        self.api.route('/list_servers', methods=['GET'])(self.list_servers)
        self.api.route('/add_server', methods=['POST'])(self.add_server)
        self.api.route('/register_ip', methods=['POST'])(self.register_ip)

        # User profile routes
        self.api.route('/profile', methods=['GET'])(self.get_profile)

        # Health check route
        self.api.route('/health', methods=['GET'])(self.health_check)
        # Comment to post route
        self.api.route('/comment', methods=['POST'])(self.create_comment)

    def create_comment(self):
        """Create a new comment on a post and append it to the original post content"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get('username')

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        content = data.get('content')
        post_id = data.get('post_id')
        if not content or not post_id:
            return jsonify({"error": "Content and post_id are required"}), 400

        # Create comment data
        timestamp = int(time.time())
        comment_data = {
            "author": username,
            "timestamp": timestamp,
            "content": content,
            "post_id": post_id
        }

        # Sign the comment data
        signature_data = f"{comment_data['timestamp']}{comment_data['author']}{comment_data['content']}"
        comment_data["signature"] = self.security.sign_data(signature_data)

        # Save comment to database
        comment_id = self.db.save_comment(comment_data)
        if not comment_id:
            logger.error(f"Failed to save comment for user: {username}")
            return jsonify({"error": "Failed to save comment"}), 500

        # Retrieve the original post
        original_post = self.db.get_post_by_id(post_id)
        if not original_post:
            logger.error(f"Original post with ID {post_id} not found")
            return jsonify({"error": "Original post not found"}), 404

        # Create a separator including a link to the original post and a timestamp.
        timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        separator = (
            f"\n\n========== INFO - Original Post ID: {post_id} | {timestamp_str} | User: {username} ==========\n"
        )
        
        # Append the comment to the original post content.
        new_content = original_post["content"] + separator + f"{content}"

        update_success = self.db.update_post(post_id, new_content)
        if not update_success:
            logger.error(f"Failed to update post {post_id} with new comment")
            return jsonify({"error": "Failed to update post with comment"}), 500

        logger.info(f"Comment created by {username} with ID: {comment_id} and appended to post {post_id}")
        return jsonify({"message": "Comment created and appended successfully", "comment_id": comment_id}), 201

    def register(self):
        """Register a new user"""
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get('username')
        password = data.get('password')

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

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # Get user from database
        user = self.db.get_user(username)
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return jsonify({"error": "Invalid credentials"}), 401

        # Verify password
        if not self.security.verify_password(password, user['password']):
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate JWT token
        token = self.security.generate_jwt(username)
        if not token:
            logger.error(f"Failed to generate token for user: {username}")
            return jsonify({"error": "Failed to generate authentication token"}), 500

        # Store token in session so we can access it in feed.html
        session['token'] = token

        # Update last login time
        self.db.update_login_time(username)

        logger.info(f"User logged in: {username}")
        return jsonify({"token": token}), 200

    def create_post(self):
        """Create a new post"""
        # Inline authentication
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or invalid"}), 401
        token = token.split("Bearer ")[1]
        payload = self.security.verify_jwt(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        username = payload.get('username')

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        content = data.get('content')
        if not content:
            return jsonify({"error": "Content is required"}), 400

        # Create post data
        timestamp = int(time.time())
        post_data = {
            "author": username,
            "timestamp": timestamp,
            "content": content
        }

        # Sign the post data
        signature_data = f"{post_data['timestamp']}{post_data['author']}{post_data['content']}"
        post_data["signature"] = self.security.sign_data(signature_data)

        # Save post to database
        post_id = self.db.save_post(post_data)
        if not post_id:
            logger.error(f"Failed to save post for user: {username}")
            return jsonify({"error": "Failed to save post"}), 500
        
        logger.info(f"Post created by {username} with ID: {post_id}")
        return jsonify({"message": "Post created successfully", "post_id": post_id}), 201
    
    def get_feed(self):
        """Get all posts from the local database"""
        posts = self.db.get_all_posts()
        return jsonify({"posts": posts}), 200
    
    def get_post(self, post_id):
        """Get a specific post by ID"""
        post = self.db.get_post_by_id(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
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
        username = payload.get('username')
        
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        server_url = data.get('server_url')
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
        
        username = data.get('username')
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
        username = payload.get('username')
        
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
        return jsonify({
            "status": "ok",
            "timestamp": int(time.time())
        }), 200

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
    logger.info(f"Database initialized at {config.get("DB_PATH")}")
    
    # Initialize security
    security = Security(config.config)
    logger.info("Security module initialized")
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder=config.get("WEB_TEMPLATE_DIR"),
                static_folder=config.get("WEB_STATIC_DIR"))
    
    app.config["SECRET_KEY"] = config.get("JWT_SECRET_KEY")
    app.config["SESSION_TYPE"] = "filesystem"
    
    # Initialize API
    api = RSSXApi(db, security)
    app.register_blueprint(api.api, url_prefix='/api')
    logger.info("API registered at /api")
    
    # Initialize Web UI if enabled
    if config.get("ENABLE_WEB_UI"):
        web_ui = WebUI(db, security, config)
        app.register_blueprint(web_ui.web, url_prefix='/')
        logger.info("Web UI registered at /")
    
    @app.route('/')
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
                    "/api/health"
                ]
            }
    
    return app, db, security, config

def run_server(config=None, host="0.0.0.0", port=5000, debug=False):
    """Run the RSSX server"""
    # Create application
    app, db, security, config = create_app(config)
    
    # Use command-line values if provided, otherwise use config
    host = host or config.get("HOST")
    port = port or config.get("PORT")
    debug = debug if debug is not None else config.get("DEBUG")
    
    # Start the server
    app.run(host=host, port=port, debug=debug)

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
    parser = argparse.ArgumentParser(description="RSSX Distributed Social Media Platform")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", help="Host address to bind to")
    parser.add_argument("--port", type=int, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-web-ui", action="store_true", help="Disable web UI")
    parser.add_argument("--client", choices=["tui", "gui", "web"], help="Run a client interface")
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config if args.config else "config.json")
    
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
            print(f"Web UI available at http://{config.get('HOST')}:{config.get('PORT')}/")
            run_server(config, args.host, args.port, args.debug)
    else:
        # Run the server by default
        run_server(config, args.host, args.port, args.debug)

if __name__ == "__main__":
    main()
