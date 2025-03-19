import os
import time
from flask import Flask, request, jsonify
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import random
# Path for storing RSA keys
PUBLIC_KEY_FILE = 'rsa_public.pem'
PRIVATE_KEY_FILE = 'rsa_private.pem'

# Flask app initialization
app = Flask(__name__)

# Directory to store posts
POSTS_DIRECTORY = 'posts'
if not os.path.exists(POSTS_DIRECTORY):
    os.makedirs(POSTS_DIRECTORY)

# Dictionary to store IP to username mapping
ip_to_username = {}

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
    return signature

def save_post(post_data):
    """Save a post to the posts folder."""
    # Create a unique post ID using timestamp
    unique_id = str(int(time.time()))  # Use timestamp as unique ID
    post_filename = f"{POSTS_DIRECTORY}/{time.strftime('%Y_%m_%d_%H_%M_%S')}_{unique_id}.rssx"
    
    # Create the post content based on the RSSX format
    post_content = f"""ID: {unique_id}
Author: {post_data['author']}
Timestamp: {post_data['timestamp']}
Content: {post_data['content']}
Signature: {post_data['signature']}
"""
    
    # Write the post to the file
    with open(post_filename, 'w') as file:
        file.write(post_content)

    print(f"Post saved as {post_filename}")
    return unique_id, post_filename  # Return the unique ID for referencing

def get_post(post_id):
    """Retrieve a post from the filesystem by post_id."""
    for filename in os.listdir(POSTS_DIRECTORY):
        if filename.endswith('.rssx'):
            post_path = os.path.join(POSTS_DIRECTORY, filename)
            with open(post_path, 'r') as file:
                content = file.read()
                if f"ID: {post_id}" in content:
                    return content
    return None  # Post not found



@app.route('/post', methods=['POST'])
def create_post():
    """Endpoint to receive and save a post."""
    # Receive post data
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    # Extract data from request
    ip = request.remote_addr  # Get the IP address of the client
    username = ip_to_username.get(ip)
    if not username:
        return jsonify({"error": "User not registered. Please register first."}), 400
    
    author = username  # Use the registered username for the post
    content = data.get('content')
    
    if not content:
        return jsonify({"error": "Missing 'content' field"}), 400
    
    # Prepare the post data
    post_data = {
        "author": author,
        "timestamp": int(time.time()),
        "content": content
    }
    
    # Sign the post data using the private key
    signature_data = f"ID: {post_data['timestamp']+random.randint(1000,9999)}Author: {post_data['author']}Timestamp: {post_data['timestamp']}Content: {post_data['content']}"
    signature = sign_data(signature_data, private_key)
    post_data["signature"] = signature.hex()  # Store signature as hex

    # Save the post to the file system
    unique_id, post_filename = save_post(post_data)
    
    # Respond to the client
    return jsonify({"message": "Post saved", "post_id": unique_id, "post_filename": post_filename}), 200

@app.route('/post/<post_id>', methods=['GET'])
def get_post_by_id(post_id):
    """Endpoint to retrieve a post by its ID."""
    post_content = get_post(post_id)
    
    if post_content:
        return jsonify({"post": post_content}), 200
    else:
        return jsonify({"error": "Post not found"}), 404

if __name__ == '__main__':
    # Load RSA keys
    public_key, private_key = load_rsa_keys()

    # Start the Flask server
    app.run(host='0.0.0.0', port=5000)
