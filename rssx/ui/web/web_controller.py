from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class WebUI:
    def __init__(self, db, security, config):
        """Initialize the Web UI with database, security, and configuration"""
        self.db = db
        self.security = security
        self.config = config
        self.web = Blueprint('web', __name__, 
                           template_folder=config.get("WEB_TEMPLATE_DIR"),
                           static_folder=config.get("WEB_STATIC_DIR"))
        self.register_routes()
    
    def register_routes(self):
        """Register all web routes"""
        # Main pages
        self.web.route('/', methods=['GET'])(self.index)
        self.web.route('/feed', methods=['GET'])(self.feed)
        self.web.route('/servers', methods=['GET', 'POST'])(self.servers)
        
        # Authentication
        self.web.route('/login', methods=['GET', 'POST'])(self.login)
        self.web.route('/register', methods=['GET', 'POST'])(self.register)
        self.web.route('/logout')(self.logout)
        
        # User
        self.web.route('/profile', methods=['GET'])(self.profile)
        
        # Posts
        self.web.route('/create_post', methods=['POST'])(self.create_post)
        
        # Before request
        self.web.before_request(self.before_request)
    
    def before_request(self):
        """Check session before each request"""
        # Add current user to template context
        if 'username' in session:
            self.current_user = session['username']
        else:
            self.current_user = None
    
    def _get_formatted_posts(self, posts_raw):
        """Format raw post data for display"""
        formatted_posts = []
        for post_raw in posts_raw:
            lines = post_raw.strip().split('\n')
            post = {}
            for line in lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    post[key.lower()] = value.strip()
            
            # Format timestamp
            if 'timestamp' in post:
                try:
                    ts = int(post['timestamp'])
                    post['timestamp_formatted'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    post['timestamp_formatted'] = 'Unknown'
            
            formatted_posts.append(post)
        
        # Sort by timestamp, newest first
        formatted_posts.sort(key=lambda x: int(x.get('timestamp', 0)) if x.get('timestamp', '').isdigit() else 0, reverse=True)
        
        return formatted_posts
    
    def index(self):
        """Render the homepage"""
        return render_template('index.html', current_user=self.current_user)
    
    def feed(self):
        """Display the post feed"""
        posts_raw = self.db.get_all_posts()
        posts = self._get_formatted_posts(posts_raw)
        
        return render_template('feed.html', 
                             current_user=self.current_user,
                             posts=posts)
    
    def servers(self):
        """Manage connected servers"""
        if request.method == 'POST':
            server_url = request.form.get('server_url')
            if server_url:
                success = self.db.add_server(server_url)
                if success:
                    flash(f"Server {server_url} added successfully", "success")
                else:
                    flash("Server already connected or failed to add", "danger")
                return redirect(url_for('web.servers'))
        
        servers = self.db.get_all_servers()
        return render_template('servers.html', 
                             current_user=self.current_user,
                             servers=servers)
    
    def login(self):
        """Handle user login"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash("Please enter both username and password", "danger")
                return render_template('login.html', current_user=self.current_user)
            
            # Get user from database
            user = self.db.get_user(username)
            if not user:
                flash("Invalid credentials", "danger")
                return render_template('login.html', current_user=self.current_user)
            
            # Verify password
            if not self.security.verify_password(password, user['password']):
                flash("Invalid credentials", "danger")
                return render_template('login.html', current_user=self.current_user)
            
            # Create session
            session['username'] = username
            session['token'] = self.security.generate_jwt(username)
            
            # Update last login time
            self.db.update_login_time(username)
            
            flash("Login successful", "success")
            return redirect(url_for('web.index'))
        
        return render_template('login.html', current_user=self.current_user)
    
    def register(self):
        """Handle user registration"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate inputs
            if not username or not password or not confirm_password:
                flash("Please fill out all fields", "danger")
                return render_template('register.html', current_user=self.current_user)
            
            if password != confirm_password:
                flash("Passwords do not match", "danger")
                return render_template('register.html', current_user=self.current_user)
            
            if len(password) < 6:
                flash("Password must be at least 6 characters long", "danger")
                return render_template('register.html', current_user=self.current_user)
            
            # Check if username already exists
            existing_user = self.db.get_user(username)
            if existing_user:
                flash("Username already taken", "danger")
                return render_template('register.html', current_user=self.current_user)
            
            # Hash password and save user
            hashed_password = self.security.hash_password(password)
            if self.db.save_user(username, hashed_password):
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for('web.login'))
            else:
                flash("Failed to register user", "danger")
                return render_template('register.html', current_user=self.current_user)
        
        return render_template('register.html', current_user=self.current_user)
    
    def logout(self):
        """Log the user out"""
        session.pop('username', None)
        session.pop('token', None)
        flash("You have been logged out", "success")
        return redirect(url_for('web.index'))
    
    def profile(self):
        """Display user profile"""
        if not self.current_user:
            flash("Please log in to view your profile", "warning")
            return redirect(url_for('web.login'))
        
        user = self.db.get_user(self.current_user)
        if not user:
            flash("User not found", "danger")
            return redirect(url_for('web.index'))
        
        # Get token expiration time
        token_exp = None
        if 'token' in session:
            try:
                payload = self.security.verify_jwt(session['token'])
                if payload and 'exp' in payload:
                    token_exp = datetime.fromtimestamp(payload['exp'])
            except Exception as e:
                logger.error(f"Error checking token expiration: {str(e)}")
        
        return render_template('profile.html', 
                             current_user=self.current_user,
                             token_exp=token_exp)
    
    def create_post(self):
        """Create a new post"""
        if not self.current_user:
            flash("Please log in to create a post", "warning")
            return redirect(url_for('web.login'))
        
        if request.method == 'POST':
            content = request.form.get('content')
            if not content:
                flash("Post content cannot be empty", "danger")
                return redirect(url_for('web.feed'))
            
            # Create post data
            timestamp = int(datetime.now().timestamp())
            post_data = {
                "author": self.current_user,
                "timestamp": timestamp,
                "content": content
            }
            
            # Sign the post data
            signature_data = f"{post_data['timestamp']}{post_data['author']}{post_data['content']}"
            post_data["signature"] = self.security.sign_data(signature_data)
            
            # Save post to database
            post_id = self.db.save_post(post_data)
            if not post_id:
                flash("Failed to create post", "danger")
            else:
                flash("Post created successfully", "success")
            
            return redirect(url_for('web.feed'))