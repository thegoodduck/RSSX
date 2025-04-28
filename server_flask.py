import os
import time
import json
import requests
import bcrypt
import jwt
from flask import Flask, request, jsonify
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import glob

# JWT Secret Key
SECRET_KEY = "your_secret_key"

# RSA Keys
PUBLIC_KEY_FILE = 'rsa_public.pem'
PRIVATE_KEY_FILE = 'rsa_private.pem'

# Flask app
app = Flask(__name__)

# Storage directories
POSTS_DIRECTORY = 'posts'
if not os.path.exists(POSTS_DIRECTORY):
    os.makedirs(POSTS_DIRECTORY)

USERS_FILE = "users.json"
SERVERS_FILE = "servers.json"

# Connected servers
connected_servers = []

if os.path.exists(SERVERS_FILE):
    with open(SERVERS_FILE, "r") as f:
        connected_servers = json.load(f)

# IP to username mapping
ip_to_username = {}

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

# RSA Key Generation
def generate_rsa_keys():
    key = RSA.generate(2048)
    with open(PUBLIC_KEY_FILE, 'wb') as pub_file:
        pub_file.write(key.publickey().export_key())
    with open(PRIVATE_KEY_FILE, 'wb') as priv_file:
        priv_file.write(key.export_key())

def load_rsa_keys():
    if not os.path.exists(PUBLIC_KEY_FILE) or not os.path.exists(PRIVATE_KEY_FILE):
        generate_rsa_keys()

    with open(PUBLIC_KEY_FILE, 'rb') as pub_file:
        public_key = RSA.import_key(pub_file.read())
    with open(PRIVATE_KEY_FILE, 'rb') as priv_file:
        private_key = RSA.import_key(priv_file.read())

    return public_key, private_key

# Load keys
public_key, private_key = load_rsa_keys()

# Sign data
def sign_data(data):
    h = SHA256.new(data.encode('utf-8'))
    signature = pkcs1_15.new(private_key).sign(h)
    return signature.hex()

# Save user
def save_user(username, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    users[username] = hashed_password
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# Authenticate user
def authenticate(username, password):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username].encode()):
        # Add expiration time (24 hours) and issued-at time 
        payload = {
            "username": username,
            "exp": int(time.time()) + 86400,  # 24 hours from now
            "iat": int(time.time())
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return None

# Decode JWT
def decode_jwt(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data.get("username")
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None
    except Exception as e:
        print(f"Error decoding token: {str(e)}")
        return None

# Save post
def save_post(post_data):
    unique_id = str(int(time.time()))
    post_filename = f"{POSTS_DIRECTORY}/{unique_id}.rssx"

    post_content = f"""ID: {unique_id}
Author: {post_data['author']}
Timestamp: {post_data['timestamp']}
Content: {post_data['content']}
Signature: {post_data['signature']}
"""

    with open(post_filename, 'w') as file:
        file.write(post_content)
    
    return unique_id, post_filename

# Get posts
def get_all_posts():
    posts = []
    for filename in os.listdir(POSTS_DIRECTORY):
        if filename.endswith('.rssx'):
            with open(os.path.join(POSTS_DIRECTORY, filename), 'r') as file:
                posts.append(file.read())
    return posts

# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400
    
    save_user(username, password)
    return jsonify({"message": "User registered successfully"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    token = authenticate(username, password)
    if token:
        return jsonify({"token": token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/post', methods=['POST'])
def create_post():
    token = request.headers.get("Authorization")
    
    # Check if token exists and has correct format
    if not token or not token.startswith("Bearer "):
        return jsonify({"error": "Authorization token is missing or invalid"}), 401
    
    # Extract the token part
    token = token.split("Bearer ")[1]
    username = decode_jwt(token)
    
    # Verify token validity
    if not username:
        # Try to get username from headers as fallback
        username = request.headers.get("Username")
        if not username:
            return jsonify({"error": "Invalid token and no username provided"}), 401
    
    data = request.json
    content = data.get('content')

    if not content:
        return jsonify({"error": "Content is required"}), 400
    
    post_data = {
        "author": username,
        "timestamp": int(time.time()),
        "content": content
    }
    
    signature_data = f"{post_data['timestamp']}{post_data['author']}{post_data['content']}"
    post_data["signature"] = sign_data(signature_data)

    unique_id, post_filename = save_post(post_data)
    
    return jsonify({"message": "Post saved", "post_id": unique_id}), 200

@app.route('/feed', methods=['GET'])
def get_feed():
    all_posts = get_all_posts()

    for server in connected_servers:
        try:
            response = requests.get(f"{server}/feed", timeout=3)
            if response.status_code == 200:
                remote_posts = response.json().get("posts", [])
                all_posts.extend(remote_posts)
        except requests.RequestException:
            print(f"Failed to fetch posts from {server}")

    return jsonify({"posts": all_posts})

@app.route('/list_servers', methods=['GET'])
def list_servers():
    return jsonify({"connected_servers": connected_servers})

@app.route('/add_server', methods=['POST'])
def add_server():
    data = request.json
    if "server_url" not in data:
        return jsonify({"error": "Missing 'server_url' field"}), 400
    
    server_url = data["server_url"]
    if server_url not in connected_servers:
        connected_servers.append(server_url)
        with open(SERVERS_FILE, "w") as f:
            json.dump(connected_servers, f)
        return jsonify({"message": f"Server {server_url} added"}), 200
    else:
        return jsonify({"error": "Server already connected"}), 400

@app.route("/post/<post_id>", methods=["GET"])
def get_post(post_id):
    post_files = glob.glob(os.path.join(POSTS_DIRECTORY, f"*_{post_id}.rssx"))
    
    if not post_files:
        return jsonify({"error": "Post not found"}), 404
    
    post_file = post_files[0]
    
    with open(post_file, "r") as file:
        post_content = file.read()
    
    return jsonify({"post": post_content}), 200

@app.route('/register', methods=['POST'])
def register_ip():
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
    app.run(host='0.0.0.0', port=5000)
