import requests
import json
import os
import jwt
import time
import sys
import getpass
from datetime import datetime

SERVER_URL = "http://127.0.0.1:5000"
TOKEN_FILE = "token.txt"
CONFIG_FILE = "config.json"

# Load configuration from file
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"server_url": SERVER_URL, "theme": "default"}

# Save configuration to file
def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

# Load the token from the file if available
def load_token():
    try:
        with open(TOKEN_FILE, 'r') as file:
            token = file.read().strip()
            # Check if token is still valid
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                exp_time = decoded.get('exp', 0)
                if exp_time and time.time() > exp_time:
                    print("Your session has expired. Please log in again.")
                    return None
                return token
            except jwt.DecodeError:
                return None
    except FileNotFoundError:
        return None

# Save the token to a file
def save_token(token):
    with open(TOKEN_FILE, 'w') as file:
        file.write(token)
        
# Pretty print for RSSX posts
def pretty_print_post(post_content):
    lines = post_content.strip().split('\n')
    post_data = {}
    for line in lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            post_data[key] = value
    
    # Format the output with colors if available
    if 'Author' in post_data and 'Content' in post_data and 'Timestamp' in post_data:
        timestamp = int(post_data.get('Timestamp', 0))
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'=' * 50}")
        print(f"Author: {post_data['Author']}")
        print(f"Date: {date_str}")
        print(f"{'-' * 50}")
        print(f"{post_data['Content']}")
        print(f"{'=' * 50}\n")
    else:
        # Fallback to raw format
        print(post_content)

# Register the user on the server
def register():
    print("\n=== User Registration ===")
    username = input("Enter username: ")
    # Hide password input for security
    password = getpass.getpass("Enter password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if password != confirm_password:
        print("Passwords don't match. Please try again.")
        return
        
    if len(password) < 6:
        print("Password must be at least 6 characters long.")
        return
        
    print("Registering user...")
    try:
        response = requests.post(f"{SERVER_URL}/register", 
                               json={"username": username, "password": password}, 
                               timeout=5)
        
        if response.status_code == 200:
            print("\n✓ Registration successful! You can now log in.")
        else:
            error = response.json().get("error", "Unknown error")
            print(f"\n✗ Registration failed: {error}")
    except requests.RequestException as e:
        print(f"\n✗ Connection error: {str(e)}")

# Login and save the JWT token to a file
def login():
    print("\n=== User Login ===")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    print("Logging in...")
    try:
        response = requests.post(f"{SERVER_URL}/login", 
                              json={"username": username, "password": password},
                              timeout=5)
        
        if response.status_code == 200:
            token = response.json().get("token")
            save_token(token)
            
            # Decode token to get expiration
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                exp_time = decoded.get('exp', 0)
                if exp_time:
                    exp_date = datetime.fromtimestamp(exp_time)
                    print(f"\n✓ Login successful! Session valid until {exp_date.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print("\n✓ Login successful!")
            except:
                print("\n✓ Login successful!")
        else:
            error = response.json().get("error", "Invalid credentials")
            print(f"\n✗ Login failed: {error}")
    except requests.RequestException as e:
        print(f"\n✗ Connection error: {str(e)}")

# Create a new post using the JWT token for authorization
def create_post():
    token = load_token()
    if not token:
        print("Please log in first.")
        return

    try:
        # Decode the JWT token to extract the username
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        username = decoded_token.get("username")
    except jwt.DecodeError:
        print("Invalid token. Please log in again.")
        return

    content = input("Enter post content: ")
    headers = {
        "Authorization": f"Bearer {token}",
        "Username": username  # Add the username to the headers
    }
    response = requests.post(f"{SERVER_URL}/post", json={"content": content}, headers=headers)

    if response.status_code == 200:
        print(f"Post successfully created: {response.json()}")
    else:
        print("Failed to create post.")

# View the feed (all posts from the server)
def get_feed():
    token = load_token()
    if not token:
        print("Please log in first.")
        return

    print("\n=== Loading Feed ===")
    headers = {"Authorization": f"Bearer {token}"}  # Use JWT token for authentication
    
    try:
        response = requests.get(f"{SERVER_URL}/feed", headers=headers, timeout=10)
        
        if response.status_code == 200:
            posts = response.json().get("posts", [])
            if not posts:
                print("No posts available.")
            else:
                print(f"\nFound {len(posts)} post(s)")
                for post in posts:
                    pretty_print_post(post)
        else:
            error = response.json().get("error", "Unknown error")
            print(f"Failed to fetch the feed: {error}")
    except requests.RequestException as e:
        print(f"Connection error: {str(e)}")

# Get server status and information
def check_server_status():
    print("\n=== Server Status ===")
    try:
        response = requests.get(f"{SERVER_URL}/list_servers", timeout=3)
        if response.status_code == 200:
            servers = response.json().get("connected_servers", [])
            print(f"✓ Server is online at {SERVER_URL}")
            print(f"Connected servers: {len(servers)}")
            if servers:
                for server in servers:
                    print(f"  - {server}")
        else:
            print(f"✗ Server responded with status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"✗ Cannot connect to server: {str(e)}")

# View user profile and session details
def view_profile():
    token = load_token()
    if not token:
        print("Please log in first.")
        return

    try:
        # Decode the JWT to get user info
        decoded = jwt.decode(token, options={"verify_signature": False})
        username = decoded.get("username", "Unknown User")
        exp_time = decoded.get("exp", 0)
        iat_time = decoded.get("iat", 0)
        
        print("\n=== User Profile ===")
        print(f"Username: {username}")
        
        if exp_time:
            exp_date = datetime.fromtimestamp(exp_time)
            print(f"Session expires: {exp_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if iat_time:
            iat_date = datetime.fromtimestamp(iat_time)
            print(f"Session started: {iat_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
        time_left = exp_time - time.time() if exp_time else 0
        if time_left > 0:
            hours, remainder = divmod(time_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            print(f"Time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        else:
            print("Session expired. Please log in again.")
            
    except jwt.DecodeError:
        print("Invalid token. Please log in again.")
        
# Show help information
def show_help():
    print("\n=== RSSX Client Help ===")
    print("RSSX is a decentralized social media platform that allows secure sharing of posts")
    print("across multiple connected servers.")
    print("\nAvailable Commands:")
    print("  1. Register - Create a new user account")
    print("  2. Login - Authenticate with your credentials")
    print("  3. Create Post - Share a message on the network")
    print("  4. View Feed - See posts from this server and connected servers")
    print("  5. Check Server - View server status and connected servers")
    print("  6. My Profile - View your user details and session information")
    print("  7. Help - Show this help information")
    print("  8. Exit - Close the application")
    print("\nSecurity Information:")
    print("- Your password is never stored in plain text")
    print("- Communication is secured with RSA signatures")
    print("- Session tokens expire after 24 hours")
    print("- Posts are cryptographically signed to verify authenticity")
    input("\nPress Enter to continue...")

# Main menu loop to select client actions
def menu():
    print("\n" + "=" * 50)
    print("    RSSX - Distributed Social Media Platform    ")
    print("=" * 50)
    
    while True:
        # Check if logged in
        token = load_token()
        status = "✓ Logged in" if token else "✗ Not logged in"
        
        # Try to get username
        username = "Guest"
        if token:
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                username = decoded.get("username", "Guest")
            except:
                pass
            
        print(f"\nUser: {username} | {status}")
        print("\n1. Register\n2. Login\n3. Create Post\n4. View Feed")
        print("5. Check Server\n6. My Profile\n7. Help\n8. Exit")
        
        choice = input("\nChoose an option: ")

        if choice == "1":
            register()
        elif choice == "2":
            login()
        elif choice == "3":
            create_post()
        elif choice == "4":
            get_feed()
        elif choice == "5":
            check_server_status()
        elif choice == "6":
            view_profile()
        elif choice == "7":
            show_help()
        elif choice == "8":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    menu()
