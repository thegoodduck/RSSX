from flask import Blueprint, request, jsonify
import logging
import time

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