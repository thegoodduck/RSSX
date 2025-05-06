import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import os
import threading
import time
from datetime import datetime

class RSSXTkinterUI:
    def __init__(self, config):
        """Initialize Tkinter UI with configuration"""
        self.config = config
        self.server_url = config.get("DEFAULT_SERVER")
        self.token = None
        self.username = None
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("RSSX Client")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Set up the main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create the tabs
        self.create_login_tab()
        self.create_register_tab()
        self.create_feed_tab()
        self.create_post_tab()
        self.create_servers_tab()
        self.create_profile_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Try to load saved token
        self.load_token()
        
        # Auto-update feed
        self.start_feed_update_thread()
    
    def create_login_tab(self):
        """Create the login tab"""
        login_frame = ttk.Frame(self.notebook)
        self.notebook.add(login_frame, text="Login")
        
        # Login form
        login_form = ttk.Frame(login_frame, padding=20)
        login_form.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(login_form, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(login_form, textvariable=self.username_var, width=30)
        username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Password
        ttk.Label(login_form, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(login_form, textvariable=self.password_var, show="*", width=30)
        password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Login button
        login_button = ttk.Button(login_form, text="Login", command=self.login)
        login_button.grid(row=2, column=1, sticky=tk.E, pady=10)
    
    def create_register_tab(self):
        """Create the register tab"""
        register_frame = ttk.Frame(self.notebook)
        self.notebook.add(register_frame, text="Register")
        
        # Register form
        register_form = ttk.Frame(register_frame, padding=20)
        register_form.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(register_form, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reg_username_var = tk.StringVar()
        reg_username_entry = ttk.Entry(register_form, textvariable=self.reg_username_var, width=30)
        reg_username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Password
        ttk.Label(register_form, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.reg_password_var = tk.StringVar()
        reg_password_entry = ttk.Entry(register_form, textvariable=self.reg_password_var, show="*", width=30)
        reg_password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Confirm Password
        ttk.Label(register_form, text="Confirm Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.reg_confirm_password_var = tk.StringVar()
        reg_confirm_password_entry = ttk.Entry(register_form, textvariable=self.reg_confirm_password_var, show="*", width=30)
        reg_confirm_password_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Register button
        register_button = ttk.Button(register_form, text="Register", command=self.register)
        register_button.grid(row=3, column=1, sticky=tk.E, pady=10)
    
    def create_feed_tab(self):
        """Create the feed tab"""
        feed_frame = ttk.Frame(self.notebook)
        self.notebook.add(feed_frame, text="Feed")
        
        # Controls
        controls_frame = ttk.Frame(feed_frame, padding=5)
        controls_frame.pack(fill=tk.X)
        
        refresh_button = ttk.Button(controls_frame, text="Refresh", command=self.get_feed)
        refresh_button.pack(side=tk.RIGHT)
        
        # Feed content
        feed_content_frame = ttk.Frame(feed_frame, padding=5)
        feed_content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.feed_text = scrolledtext.ScrolledText(feed_content_frame, wrap=tk.WORD)
        self.feed_text.pack(fill=tk.BOTH, expand=True)
        self.feed_text.config(state=tk.DISABLED)
    
    def create_post_tab(self):
        """Create the post tab"""
        post_frame = ttk.Frame(self.notebook)
        self.notebook.add(post_frame, text="Create Post")
        
        # Post form
        post_form = ttk.Frame(post_frame, padding=20)
        post_form.pack(fill=tk.BOTH, expand=True)
        
        # Content
        ttk.Label(post_form, text="Post Content:").pack(anchor=tk.W, pady=5)
        self.post_content_var = tk.StringVar()
        self.post_content_text = scrolledtext.ScrolledText(post_form, wrap=tk.WORD, height=10)
        self.post_content_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Post button
        post_button = ttk.Button(post_form, text="Post", command=self.create_post)
        post_button.pack(side=tk.RIGHT, pady=10)
    
    def create_servers_tab(self):
        """Create the servers tab"""
        servers_frame = ttk.Frame(self.notebook)
        self.notebook.add(servers_frame, text="Servers")
        
        # Servers form
        servers_form = ttk.Frame(servers_frame, padding=20)
        servers_form.pack(fill=tk.BOTH, expand=True)
        
        # Add server
        ttk.Label(servers_form, text="Add Server:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_url_var = tk.StringVar()
        server_url_entry = ttk.Entry(servers_form, textvariable=self.server_url_var, width=40)
        server_url_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        add_server_button = ttk.Button(servers_form, text="Add", command=self.add_server)
        add_server_button.grid(row=0, column=2, padx=5)
        
        # Server list
        ttk.Label(servers_form, text="Connected Servers:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Create a frame for the server list
        server_list_frame = ttk.Frame(servers_form)
        server_list_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW)
        servers_form.rowconfigure(2, weight=1)
        servers_form.columnconfigure(1, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(server_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox
        self.server_listbox = tk.Listbox(server_list_frame)
        self.server_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Link listbox and scrollbar
        self.server_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.server_listbox.yview)
        
        # Refresh button
        refresh_button = ttk.Button(servers_form, text="Refresh", command=self.get_servers)
        refresh_button.grid(row=3, column=0, pady=10)
    
    def create_profile_tab(self):
        """Create the profile tab"""
        profile_frame = ttk.Frame(self.notebook)
        self.notebook.add(profile_frame, text="Profile")
        
        # Profile content
        profile_content = ttk.Frame(profile_frame, padding=20)
        profile_content.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(profile_content, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.profile_username_var = tk.StringVar()
        profile_username_label = ttk.Label(profile_content, textvariable=self.profile_username_var)
        profile_username_label.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Session expiry
        ttk.Label(profile_content, text="Session Expires:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.session_expiry_var = tk.StringVar()
        session_expiry_label = ttk.Label(profile_content, textvariable=self.session_expiry_var)
        session_expiry_label.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Logout button
        logout_button = ttk.Button(profile_content, text="Logout", command=self.logout)
        logout_button.grid(row=2, column=1, sticky=tk.E, pady=10)
    
    def login(self):
        """Login to the server"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        try:
            response = requests.post(
                f"{self.server_url}/login",
                json={"username": username, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("token")
                self.username = username
                
                # Save token to file
                self.save_token()
                
                # Update UI
                self.profile_username_var.set(username)
                self.update_token_info()
                self.status_var.set(f"Logged in as {username}")
                
                # Switch to feed tab
                self.notebook.select(2)  # Feed tab
                
                # Get feed data
                self.get_feed()
                
                messagebox.showinfo("Success", "Login successful")
            else:
                error_msg = response.json().get("error", "Invalid credentials")
                messagebox.showerror("Login Failed", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def register(self):
        """Register a new user"""
        username = self.reg_username_var.get()
        password = self.reg_password_var.get()
        confirm_password = self.reg_confirm_password_var.get()
        
        if not username or not password or not confirm_password:
            messagebox.showerror("Error", "Please fill out all fields")
            return
        
        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long")
            return
        
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={"username": username, "password": password},
                timeout=5
            )
            
            if response.status_code == 200 or response.status_code == 201:
                messagebox.showinfo("Success", "Registration successful! You can now log in.")
                
                # Clear registration fields
                self.reg_username_var.set("")
                self.reg_password_var.set("")
                self.reg_confirm_password_var.set("")
                
                # Switch to login tab
                self.notebook.select(0)  # Login tab
            else:
                error_msg = response.json().get("error", "Registration failed")
                messagebox.showerror("Registration Failed", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def get_feed(self):
        """Get the post feed"""
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            self.notebook.select(0)  # Login tab
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.server_url}/feed", headers=headers, timeout=5)
            
            if response.status_code == 200:
                posts = response.json().get("posts", [])
                
                # Clear the feed text
                self.feed_text.config(state=tk.NORMAL)
                self.feed_text.delete(1.0, tk.END)
                
                if not posts:
                    self.feed_text.insert(tk.END, "No posts available.\n")
                else:
                    for post in posts:
                        self.format_post(post)
                
                self.feed_text.config(state=tk.DISABLED)
            else:
                error_msg = response.json().get("error", "Failed to get feed")
                messagebox.showerror("Feed Error", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def format_post(self, post_content):
        """Format a post for display in the feed"""
        self.feed_text.insert(tk.END, "=" * 50 + "\n")
        
        lines = post_content.strip().split('\n')
        post_data = {}
        
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                post_data[key] = value
        
        if 'Author' in post_data:
            self.feed_text.insert(tk.END, f"Author: {post_data['Author']}\n")
        
        if 'Timestamp' in post_data:
            try:
                timestamp = int(post_data['Timestamp'])
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                self.feed_text.insert(tk.END, f"Date: {date_str}\n")
            except (ValueError, TypeError):
                pass
        
        self.feed_text.insert(tk.END, "-" * 50 + "\n")
        
        if 'Content' in post_data:
            self.feed_text.insert(tk.END, f"{post_data['Content']}\n")
        
        self.feed_text.insert(tk.END, "=" * 50 + "\n\n")
    
    def create_post(self):
        """Create a new post"""
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            self.notebook.select(0)  # Login tab
            return
        
        content = self.post_content_text.get(1.0, tk.END).strip()
        
        if not content:
            messagebox.showerror("Error", "Post content cannot be empty")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.server_url}/post",
                json={"content": content},
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200 or response.status_code == 201:
                messagebox.showinfo("Success", "Post created successfully")
                
                # Clear the post content
                self.post_content_text.delete(1.0, tk.END)
                
                # Refresh the feed
                self.get_feed()
                
                # Switch to feed tab
                self.notebook.select(2)  # Feed tab
            else:
                error_msg = response.json().get("error", "Failed to create post")
                messagebox.showerror("Post Error", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def get_servers(self):
        """Get the list of connected servers"""
        try:
            response = requests.get(f"{self.server_url}/list_servers", timeout=5)
            
            if response.status_code == 200:
                servers = response.json().get("connected_servers", [])
                
                # Clear the server list
                self.server_listbox.delete(0, tk.END)
                
                for server in servers:
                    self.server_listbox.insert(tk.END, server)
            else:
                error_msg = response.json().get("error", "Failed to get servers")
                messagebox.showerror("Server Error", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def add_server(self):
        """Add a new server"""
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            self.notebook.select(0)  # Login tab
            return
        
        server_url = self.server_url_var.get()
        
        if not server_url:
            messagebox.showerror("Error", "Server URL cannot be empty")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.server_url}/add_server",
                json={"server_url": server_url},
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200 or response.status_code == 201:
                messagebox.showinfo("Success", f"Server {server_url} added successfully")
                
                # Clear the server URL field
                self.server_url_var.set("")
                
                # Refresh the server list
                self.get_servers()
            else:
                error_msg = response.json().get("error", "Failed to add server")
                messagebox.showerror("Server Error", error_msg)
        
        except requests.RequestException as e:
            messagebox.showerror("Connection Error", str(e))
    
    def logout(self):
        """Log out the current user"""
        self.token = None
        self.username = None
        
        # Clear token file
        if os.path.exists("token.txt"):
            try:
                os.remove("token.txt")
            except Exception:
                pass
        
        # Update UI
        self.profile_username_var.set("")
        self.session_expiry_var.set("")
        self.status_var.set("Not connected")
        
        # Clear the feed
        self.feed_text.config(state=tk.NORMAL)
        self.feed_text.delete(1.0, tk.END)
        self.feed_text.config(state=tk.DISABLED)
        
        # Switch to login tab
        self.notebook.select(0)  # Login tab
        
        messagebox.showinfo("Success", "Logged out successfully")
    
    def save_token(self):
        """Save the token to a file"""
        if self.token and self.username:
            try:
                with open("token.txt", "w") as file:
                    json.dump({"token": self.token, "username": self.username}, file)
            except Exception as e:
                print(f"Error saving token: {str(e)}")
    
    def load_token(self):
        """Load the token from a file"""
        if os.path.exists("token.txt"):
            try:
                with open("token.txt", "r") as file:
                    data = json.load(file)
                    self.token = data.get("token")
                    self.username = data.get("username")
                    
                    if self.token and self.username:
                        # Update UI
                        self.profile_username_var.set(self.username)
                        self.update_token_info()
                        self.status_var.set(f"Logged in as {self.username}")
                        
                        # Get feed data
                        self.get_feed()
                        
                        # Get servers
                        self.get_servers()
            except Exception as e:
                print(f"Error loading token: {str(e)}")
    
    def update_token_info(self):
        """Update token information in the UI"""
        if self.token:
            try:
                # Decode the token to get expiration time
                # This assumes a JWT token format
                token_parts = self.token.split('.')
                if len(token_parts) == 3:
                    # Decode the payload (middle part)
                    import base64
                    payload = token_parts[1]
                    # Add padding if needed
                    padding = 4 - (len(payload) % 4)
                    if padding < 4:
                        payload += '=' * padding
                    
                    decoded = base64.b64decode(payload)
                    payload_data = json.loads(decoded)
                    
                    if 'exp' in payload_data:
                        exp_time = datetime.fromtimestamp(payload_data['exp'])
                        self.session_expiry_var.set(exp_time.strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        self.session_expiry_var.set("Unknown")
                else:
                    self.session_expiry_var.set("Unknown format")
            except Exception as e:
                print(f"Error updating token info: {str(e)}")
                self.session_expiry_var.set("Error parsing token")
    
    def start_feed_update_thread(self):
        """Start a thread to update the feed periodically"""
        def update_feed_thread():
            while True:
                if self.token:
                    # Only update if we're on the feed tab
                    if self.notebook.index(self.notebook.select()) == 2:  # Feed tab
                        self.get_feed()
                # Sleep for 30 seconds
                time.sleep(30)
        
        # Start the thread
        thread = threading.Thread(target=update_feed_thread, daemon=True)
        thread.start()
    
    def run(self):
        """Run the Tkinter UI"""
        self.root.mainloop()

def launch_tkinter_ui(config):
    """Launch the Tkinter UI"""
    ui = RSSXTkinterUI(config)
    ui.run()
    
if __name__ == "__main__":
    # If run directly, create a basic config and start the UI
    from rssx.utils.config import Config
    config = Config()
    launch_tkinter_ui(config)