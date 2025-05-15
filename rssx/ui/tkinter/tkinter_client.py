import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import os
import tkinter.simpledialog as simpledialog
from datetime import datetime

_temp_root = tk.Tk()
_temp_root.withdraw()
default_server_url = simpledialog.askstring("Server URL", "Enter the server URL:", initialvalue="http://localhost:5000")
_temp_root.destroy()

if default_server_url:
    os.environ["DEFAULT_SERVER"] = default_server_url

class RSSXTkinterUI:
    def __init__(self, config):
        self.config = config
        self.server_url = config.get("DEFAULT_SERVER") or os.environ.get("DEFAULT_SERVER") or "http://localhost:5000"
        self.token = None
        self.username = None

        self.root = tk.Tk()
        self.root.title("RSSX Client")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)

        self.control_panel = ttk.Frame(self.root)
        self.control_panel.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_button = ttk.Button(self.control_panel, text="Refresh", command=self.refresh_feed)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.login_button = ttk.Button(self.control_panel, text="Login", command=self.show_login_dialog)
        self.login_button.pack(side=tk.LEFT, padx=5)

        self.create_post_button = ttk.Button(self.control_panel, text="Create Post", command=self.show_create_post_dialog)
        self.create_post_button.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        self.status_label = ttk.Label(self.control_panel, textvariable=self.status_var)
        self.status_label.pack(side=tk.RIGHT, padx=20)

        self.feed_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED)
        self.feed_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.load_token()
        self.refresh_feed()

    def show_login_dialog(self):
        login_dialog = tk.Toplevel(self.root)
        login_dialog.title("Login")
        login_dialog.geometry("300x150")
        login_dialog.transient(self.root)
        login_dialog.grab_set()

        ttk.Label(login_dialog, text="Username:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(login_dialog, textvariable=username_var, width=20)
        username_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(login_dialog, text="Password:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(login_dialog, textvariable=password_var, show="*", width=20)
        password_entry.grid(row=1, column=1, padx=10, pady=10)

        def do_login():
            username = username_var.get()
            password = password_var.get()
            if not username or not password:
                messagebox.showerror("Error", "Please enter both username and password")
                return

            try:
                response = requests.post(
                    f"{self.server_url}/api/login",
                    json={"username": username, "password": password},
                    timeout=5
                )
                if response.status_code == 200:
                    token_data = response.json()
                    self.token = token_data.get("token")
                    self.username = username
                    self.save_token()
                    self.status_var.set(f"Logged in as {username}")
                    self.refresh_feed()
                    messagebox.showinfo("Login", "Login successful!")
                    login_dialog.destroy()
                else:
                    error = response.json().get("error", "Invalid credentials")
                    messagebox.showerror("Login Failed", error)
            except Exception as e:
                messagebox.showerror("Error", f"Login failed: {e}")

        button_frame = ttk.Frame(login_dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Cancel", command=login_dialog.destroy).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Login", command=do_login).pack(side=tk.RIGHT, padx=10)

    def show_create_post_dialog(self):
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            return

        post_dialog = tk.Toplevel(self.root)
        post_dialog.title("Create Post")
        post_dialog.geometry("400x300")
        post_dialog.transient(self.root)
        post_dialog.grab_set()

        ttk.Label(post_dialog, text="Post Content:").pack(anchor="w", padx=10, pady=5)
        content_text = scrolledtext.ScrolledText(post_dialog, wrap=tk.WORD, height=10)
        content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def do_post():
            content = content_text.get("1.0", tk.END).strip()
            if not content:
                messagebox.showerror("Error", "Post content cannot be empty")
                return

            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.post(
                    f"{self.server_url}/api/post",
                    json={"content": content},
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 201:
                    messagebox.showinfo("Success", "Post created successfully")
                    self.refresh_feed()
                    post_dialog.destroy()
                else:
                    error = response.json().get("error", "Failed to create post")
                    messagebox.showerror("Error", error)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create post: {e}")

        button_frame = ttk.Frame(post_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(button_frame, text="Cancel", command=post_dialog.destroy).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Post", command=do_post).pack(side=tk.RIGHT)

    def show_comment_dialog(self, post_id):
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            return

        comment_dialog = tk.Toplevel(self.root)
        comment_dialog.title("Add Comment")
        comment_dialog.geometry("400x300")
        comment_dialog.transient(self.root)
        comment_dialog.grab_set()

        ttk.Label(comment_dialog, text="Comment:").pack(anchor="w", padx=10, pady=5)
        comment_text = scrolledtext.ScrolledText(comment_dialog, wrap=tk.WORD, height=10)
        comment_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def do_comment():
            content = comment_text.get("1.0", tk.END).strip()
            if not content:
                messagebox.showerror("Error", "Comment cannot be empty")
                return

            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = requests.post(
                    f"{self.server_url}/api/comment",
                    json={"post_id": post_id, "content": content},
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 201:
                    messagebox.showinfo("Success", "Comment added successfully")
                    self.refresh_feed()
                    comment_dialog.destroy()
                else:
                    error = response.json().get("error", "Failed to add comment")
                    messagebox.showerror("Error", error)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add comment: {e}")

        button_frame = ttk.Frame(comment_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(button_frame, text="Cancel", command=comment_dialog.destroy).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Comment", command=do_comment).pack(side=tk.RIGHT)

    def refresh_feed(self):
        if not self.token:
            self.feed_text.config(state=tk.NORMAL)
            self.feed_text.delete("1.0", tk.END)
            self.feed_text.insert(tk.END, "Please log in to view the feed.")
            self.feed_text.config(state=tk.DISABLED)
            return

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.server_url}/api/feed", headers=headers, timeout=10)
            if response.status_code == 200:
                posts = response.json().get("posts", [])
                self.feed_text.config(state=tk.NORMAL)
                self.feed_text.delete("1.0", tk.END)
                for post in posts:
                    self.display_post(post)
                self.feed_text.config(state=tk.DISABLED)
            else:
                error = response.json().get("error", "Failed to fetch feed")
                messagebox.showerror("Error", error)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch feed: {e}")

    def display_post(self, post):
        author = post.get("author", "Unknown")
        content = post.get("content", "")
        timestamp = post.get("timestamp", 0)
        post_id = post.get("id", "Unknown")
        upvotes = post.get("upvotes", 0)
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Display the post content
        self.feed_text.insert(tk.END, f"Author: {author}\nDate: {date_str}\nContent:\n{content}\nUpvotes: {upvotes}\n\n")

        # Add an upvote button for each post
        upvote_button = ttk.Button(self.root, text="Upvote", command=lambda: self.upvote_post(post_id))
        self.feed_text.window_create(tk.END, window=upvote_button)

        # Add a comment button for each post
        comment_button = ttk.Button(self.root, text="Comment", command=lambda: self.show_comment_dialog(post_id))
        self.feed_text.window_create(tk.END, window=comment_button)

        self.feed_text.insert(tk.END, "\n" + ("="*40) + "\n\n")

    def upvote_post(self, post_id):
        if not self.token:
            messagebox.showwarning("Warning", "Please log in first")
            return

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.server_url}/api/upvote",
                json={"post_id": post_id},
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                messagebox.showinfo("Success", "Post upvoted successfully")
                self.refresh_feed()
            else:
                error = response.json().get("error", "Failed to upvote post")
                messagebox.showerror("Error", error)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upvote post: {e}")

    def save_token(self):
        if self.token and self.username:
            try:
                with open("token.txt", "w") as file:
                    json.dump({"token": self.token, "username": self.username}, file)
            except Exception as e:
                print(f"Error saving token: {e}")

    def load_token(self):
        if os.path.exists("token.txt"):
            try:
                with open("token.txt", "r") as file:
                    data = json.load(file)
                    self.token = data.get("token")
                    self.username = data.get("username")
                    if self.token and self.username:
                        self.status_var.set(f"Logged in as {self.username}")
            except Exception as e:
                print(f"Error loading token: {e}")

    def run(self):
        self.root.mainloop()

def launch_tkinter_ui(config):
    ui = RSSXTkinterUI(config)
    ui.run()

if __name__ == "__main__":
    import sys
    sys.path.append('/home/viktor/Documents/RSSX/rssx')
    from utils.config import Config
    config = Config()
    launch_tkinter_ui(config)