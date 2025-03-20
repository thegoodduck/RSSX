import os
import time
import json
import requests
from flask import Flask, request, jsonify
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import random
import glob
# Path for storing RSA keys
PUBLIC_KEY_FILE = 'rsa_public.pem'
PRIVATE_KEY_FILE = 'rsa_private.pem'

# Flask app initialization
app = Flask(__name__)

# Directory to store posts
POSTS_DIRECTORY = 'posts'
if not os.path.exists(POSTS_DIRECTORY):
    os.makedirs(POSTS_DIRECTORY)

# Dictionary to store IP-to-username mapping
ip_to_username = {}

# List of connected servers
SERVERS_FILE = "servers.json"
connected_servers = []

# Load servers from file
if os.path.exists(SERVERS_FILE):
    with open(SERVERS_FILE, "r") as f:
        connected_servers = json.load(f)

# Load RSA keys
def generate_rsa_keys():
    key = RSA.generate(2048)
    with open(PUBLIC_KEY_FILE, 'wb') as pub_file:
        pub_file.write(key.publickey().export_key())
    with open(PRIVATE_KEY_FILE, 'wb') as priv_file:
        priv_file.write(key.export_key())
    print("RSA key pair generated.")

def load_rsa_keys():
    """Load RSA keys from files."""
    if not os.path.exists(PUBLIC_KEY_FILE) or not os.path.exists(PRIVATE_KEY_FILE):
        print("RSA keys not found. Generating new keys...")
        generate_rsa_keys()
    
    with open(PUBLIC_KEY_FILE, 'rb') as pub_file:
        public_key = RSA.import_key(pub_file.read())
    with open(PRIVATE_KEY_FILE, 'rb') as priv_file:
        private_key = RSA.import_key(priv_file.read())
    
    return public_key, private_key

# Generate RSA signatures for posts
def sign_data(data, private_key):
    """Sign data using the RSA private key."""
    h = SHA256.new(data.encode('utf-8'))  # Hash the data
    signature = pkcs1_15.new(private_key).sign(h)  # Sign the hash
    return signature.hex()  # Convert to hex

def save_post(post_data):
    """Save a post to the posts folder."""
    unique_id = str(int(time.time()))  # Use timestamp as unique ID
    post_filename = f"{POSTS_DIRECTORY}/{time.strftime('%Y_%m_%d_%H_%M_%S')}_{unique_id}.rssx"
    
    post_content = f"""ID: {unique_id}
Author: {post_data['author']}
Timestamp: {post_data['timestamp']}
Content: {post_data['content']}
Signature: {post_data['signature']}
"""
    
    with open(post_filename, 'w') as file:
        file.write(post_content)

    print(f"Post saved as {post_filename}")
    return unique_id, post_filename  # Return the unique ID for referencing

def get_all_posts():
    """Retrieve all posts from the filesystem."""
    posts = []
    for filename in os.listdir(POSTS_DIRECTORY):
        if filename.endswith('.rssx'):
            post_path = os.path.join(POSTS_DIRECTORY, filename)
            with open(post_path, 'r') as file:
                posts.append(file.read())
    return posts


@app.route('/post', methods=['POST'])
def create_post():
    """Endpoint to receive and save a post."""
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    ip = request.remote_addr  
    username = ip_to_username.get(ip)
    if not username:
        return jsonify({"error": "User not registered. Please register first."}), 400
    
    content = data.get('content')
    if not content:
        return jsonify({"error": "Missing 'content' field"}), 400
    
    post_data = {
        "author": username,
        "timestamp": int(time.time()),
        "content": content
    }
    
    signature_data = f"ID: {post_data['timestamp']}Author: {post_data['author']}Timestamp: {post_data['timestamp']}Content: {post_data['content']}"
    post_data["signature"] = sign_data(signature_data, private_key)

    unique_id, post_filename = save_post(post_data)
    
    return jsonify({"message": "Post saved", "post_id": unique_id, "post_filename": post_filename}), 200


@app.route('/list_servers', methods=['GET'])
def list_servers():
    """Return a list of all connected servers."""
    return jsonify({"connected_servers": connected_servers})

@app.route("/post/<post_id>", methods=["GET"])
def get_post(post_id):
    """Fetch a specific post by ID by searching for it in filenames."""
    post_files = glob.glob(os.path.join(POSTS_DIRECTORY, f"*_{post_id}.rssx"))  # Find matching file
    
    if not post_files:
        return jsonify({"error": "Post not found"}), 404
    
    post_file = post_files[0]  # Assume there's only one matching file
    
    with open(post_file, "r") as file:
        post_content = file.read()
    
    return jsonify({"post": post_content}), 200
@app.route('/add_server', methods=['POST'])
def add_server():
    """Add a new server to the network."""
    data = request.json
    if "server_url" not in data:
        return jsonify({"error": "Missing 'server_url' field"}), 400
    
    server_url = data["server_url"]
    if server_url not in connected_servers:
        connected_servers.append(server_url)
        with open(SERVERS_FILE, "w") as f:
            json.dump(connected_servers, f)  # Save updated server list
        return jsonify({"message": f"Server {server_url} added"}), 200
    else:
        return jsonify({"error": "Server already connected"}), 400


@app.route('/feed', methods=['GET'])
def get_feed():
    """Return posts from this server and all connected servers."""
    all_posts = get_all_posts()  # Get local posts

    # Fetch posts from connected servers
    for server in connected_servers:
        try:
            response = requests.get(f"{server}/feed", timeout=3)
            if response.status_code == 200:
                remote_posts = response.json().get("posts", [])
                all_posts.extend(remote_posts)
        except requests.RequestException:
            print(f"Failed to fetch posts from {server}")

    return jsonify({"posts": all_posts})


@app.route('/register', methods=['POST'])
def register():
    """Register a username for the client IP."""
    data = request.json
    if not data or 'username' not in data:
        return jsonify({"error": "Missing 'username' field"}), 400
    
    username = data['username']
    ip = request.remote_addr  

    if username in ip_to_username.values():
        return jsonify({"error": "Username already taken"}), 400

    ip_to_username[ip] = username
    return jsonify({"message": f"User '{username}' registered successfully"}), 200


if __name__ == '__main__':
    public_key, private_key = load_rsa_keys()
    app.run(host='0.0.0.0', port=5000)
