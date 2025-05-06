# RSSX - Distributed Social Media Platform

RSSX is a decentralized social media platform designed to empower users with control over their data and interactions. It provides a robust API, a web-based UI, and a Tkinter-based desktop client for seamless interaction. Built with Flask, SQLAlchemy, and modern web technologies, RSSX is a scalable and secure solution for distributed social networking.

---

## Features

- **Decentralized Architecture**: Connect with multiple servers for a distributed social experience.
- **User Authentication**: Secure login and registration with JWT-based authentication.
- **Interactive Feed**: View and interact with posts in real-time.
- **Cross-Platform Clients**: Access via web, desktop (Tkinter), or API.
- **Extensible API**: RESTful API for developers to build custom integrations.

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/rssx.git
cd rssx
```

### 2. Set Up a Python Virtual Environment
It is recommended to use a virtual environment to manage dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies
Install the required Python packages using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Configure the Application
Ensure the configuration file (`config.json` or similar) is set up correctly. Example:
```json
{
    "DEFAULT_SERVER": "http://localhost:5000",
    "DB_PATH": "rssx.db",
    "JWT_SECRET_KEY": "your_secret_key",
    "ENABLE_WEB_UI": true,
    "WEB_TEMPLATE_DIR": "rssx/templates",
    "WEB_STATIC_DIR": "rssx/static"
}
```

### 5. Initialize the Database
Run the following command to set up the database:
```bash
python3 -m rssx.database.db
```

### 6. Run the Server
Start the Flask server on port 5000:
```bash
python3 server_flask.py
```
The server will be accessible at `http://localhost:5000`.

---

## Running the Clients

### Web Client
Access the web client by navigating to `http://localhost:5000` in your browser.

### Tkinter Desktop Client
Run the Tkinter client with:
```bash
python3 rssx/ui/tkinter/tkinter_client.py
```

---

## Testing
Run the test suite using `pytest`:
```bash
pytest
```

---

## Project Structure
```
RSSX/
├── rssx/
│   ├── api/                # REST API implementation
│   ├── database/           # Database models and utilities
│   ├── security/           # Security and authentication
│   ├── templates/          # HTML templates for the web UI
│   ├── static/             # Static assets (CSS, JS, images)
│   ├── ui/                 # Client implementations (Tkinter, Web)
│   └── utils/              # Utility modules (config, logging)
├── server_flask.py         # Main server entry point
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

---

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

---

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Contact
For questions or support, please contact [your_email@example.com].

---

**Decentralized Social Media Protocol Specification**

## 1. Overview
This document defines the syntax and structure of a decentralized social media protocol that uses a minimal text-based format. The protocol supports posts and comments, ensuring authenticity through RSA cryptographic signatures and a caching mechanism that defers data management to participating servers.

## 2. Data Format
Each post or comment follows a structured key-value format, separated by colons (`:`). Entries are delimited by `---` to distinguish separate posts and comments.

### 2.1 Post Structure
A post consists of the following fields:
```
ID: <unique_post_id>
Author: <username_or_public_key_identifier>
Timestamp: <unix_timestamp>
Content: <text_of_the_post>
Signature: <base64_encoded_rsa_signature>
```

#### Example Post
```
ID: 123456
Author: Alice
Timestamp: 1710873600
Content: This is my first post on the decentralized network!
Signature: BASE64_ENCODED_RSA_SIGNATURE
```

### 2.2 Comment Structure
A comment is linked to a post using the `Parent-ID` field.
```
ID: <unique_comment_id>
Parent-ID: <referenced_post_id>
Author: <username_or_public_key_identifier>
Timestamp: <unix_timestamp>
Content: <text_of_the_comment>
Signature: <base64_encoded_rsa_signature>
```

#### Example Comment
```
ID: 987654
Parent-ID: 123456
Author: Bob
Timestamp: 1710873620
Content: I agree! This protocol is awesome.
Signature: BASE64_ENCODED_RSA_SIGNATURE
```

## 3. Signature Generation
To ensure authenticity, each post or comment must be signed using RSA. The signature is generated from the following concatenated fields:
```
<ID + Author + Timestamp + Content>
```
The resulting hash is then signed using the author's private key and encoded in Base64.

## 4. Caching and Decentralization
- Servers store posts and comments temporarily but defer to client IPs for content retrieval.
- Each server logs IPs that have interacted with posts.
- Clients request missing data from the original IP of a post’s author before relying on other sources.
- This reduces centralized moderation and ensures the integrity of the content.

## 5. Future Enhancements
- Support for multimedia links.
- Reputation system based on verified authors.
- End-to-end encryption for private messages.



