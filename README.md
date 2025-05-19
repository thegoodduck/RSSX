# RSSX: Federated Encrypted Social Media Platform

RSSX is a secure, federated, and optionally end-to-end encrypted social media platform. It features a Flask backend, a modern web frontend, and supports cross-server (federated) post sharing with encryption, spam filtering, rate limiting, and user-friendly error handling.

---

## Features
- **User registration and login** with JWT authentication
- **Create, upvote, downvote, and comment** on posts
- **Federation:** Share posts securely between servers
- **Encryption:** Posts can be encrypted for each server
- **Spam filtering** and **rate limiting**
- **Modern web UI** (Bootstrap-based)

---

## Getting Started

### Prerequisites
- Python 3.8+
- `pip install -r requirements.txt`

### Running the Server

```bash
python server_flask.py --host 127.0.0.1 --port 5000
```

- The web UI will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- To test federation, run a second server on a different port and add it via the web UI.

### Configuration
- Edit `config.json` for database paths, JWT secret, and key file locations.

---

## API Endpoints

### User Authentication
- `POST /api/register` — Register a new user
  - Body: `{ "username": str, "password": str }`
- `POST /api/login` — Login and get JWT token
  - Body: `{ "username": str, "password": str }`

### Posts
- `POST /api/post` — Create a new post (JWT required)
  - Body: `{ "content": str }`
- `GET /api/feed` — Get all posts (with comments)
- `GET /api/post/<post_id>` — Get a specific post (with comments)
- `POST /api/upvote` — Upvote a post (JWT required)
  - Body: `{ "post_id": str }`
- `POST /api/downvote` — Downvote a post (JWT required)
  - Body: `{ "post_id": str }`

### Comments
- `POST /api/comment` — Add a comment to a post (JWT required)
  - Body: `{ "post_id": str, "content": str }`

### Federation
- `GET /api/public_key` — Get this server's public key (for federation)
- `POST /api/receive_post` — Receive a federated post (encrypted for this server)
  - Body: `{ "author": str, "timestamp": int, "content": str (encrypted), "signature": str, "federated_from": str }`
- `GET /api/list_servers` — List all connected federated servers
- `POST /api/add_server` — Add a new federated server (JWT required)
  - Body: `{ "server_url": str }`

### Miscellaneous
- `GET /api/health` — Health check
- `GET /api/profile` — Get current user's profile (JWT required)
- `POST /api/register_ip` — Register IP address with username (for P2P, not used in web UI)

---

## Federation How-To
1. Start two servers on different ports.
2. On server A, add server B's URL in the "Add Federated Server" form.
3. When you post on server A, the post will be encrypted for server B and sent to it.
4. Server B will decrypt and display the post in its feed.

---

## Security Notes
- By default, local posts are stored as plaintext. Federated posts are encrypted for the destination server and decrypted server-side (not end-to-end encrypted).
- All API endpoints requiring authentication expect a JWT in the `Authorization: Bearer <token>` header.

---

## Development
- Flask backend: `server_flask.py`, API logic in `rssx/api/api.py`
- Database: SQLite, logic in `rssx/database/db.py`
- Security/crypto: `rssx/security/crypto.py`
- Web UI: Jinja templates in `rssx/templates/`, JS in `feed.html`

---

## License
MIT
