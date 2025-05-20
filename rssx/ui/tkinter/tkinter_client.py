import customtkinter as ctk
import requests
from tkinter import messagebox, simpledialog

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ServerTab:
    def __init__(self, parent, server_url):
        self.parent = parent
        self.server_url = server_url
        self.token = None
        self.username = None
        self.frame = ctk.CTkFrame(parent.tabs_area, corner_radius=15)
        self.frame.pack(fill="both", expand=True)
        self.show_login()

    def show_login(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        label = ctk.CTkLabel(self.frame, text=f"Login to RSSX\n{self.server_url}", font=("Segoe UI", 22, "bold"))
        label.pack(pady=30)
        self.username_entry = ctk.CTkEntry(self.frame, placeholder_text="Username")
        self.username_entry.pack(pady=10)
        self.password_entry = ctk.CTkEntry(self.frame, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=10)
        login_btn = ctk.CTkButton(self.frame, text="Login", command=self.login)
        login_btn.pack(pady=20)
        register_btn = ctk.CTkButton(self.frame, text="Register", command=self.show_register)
        register_btn.pack(pady=5)

    def show_register(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        label = ctk.CTkLabel(self.frame, text=f"Register for RSSX\n{self.server_url}", font=("Segoe UI", 22, "bold"))
        label.pack(pady=30)
        self.reg_username_entry = ctk.CTkEntry(self.frame, placeholder_text="Username")
        self.reg_username_entry.pack(pady=10)
        self.reg_password_entry = ctk.CTkEntry(self.frame, placeholder_text="Password", show="*")
        self.reg_password_entry.pack(pady=10)
        register_btn = ctk.CTkButton(self.frame, text="Register", command=self.register)
        register_btn.pack(pady=20)
        back_btn = ctk.CTkButton(self.frame, text="Back to Login", command=self.show_login)
        back_btn.pack(pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        try:
            resp = requests.post(f"{self.server_url}/login", json={"username": username, "password": password})
            if resp.status_code == 200:
                self.token = resp.json().get("token")
                self.username = username
                self.show_feed()
            else:
                messagebox.showerror("Login Failed", resp.json().get("error", "Unknown error"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def register(self):
        username = self.reg_username_entry.get()
        password = self.reg_password_entry.get()
        try:
            resp = requests.post(f"{self.server_url}/register", json={"username": username, "password": password})
            if resp.status_code == 200:
                messagebox.showinfo("Success", "Registration successful! Please log in.")
                self.show_login()
            else:
                messagebox.showerror("Registration Failed", resp.json().get("error", "Unknown error"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_feed(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        header = ctk.CTkLabel(self.frame, text="Feed", font=("Segoe UI", 22, "bold"))
        header.pack(pady=20)
        post_btn = ctk.CTkButton(self.frame, text="New Post", command=self.show_new_post)
        post_btn.pack(pady=10)
        self.feed_frame = ctk.CTkScrollableFrame(self.frame, width=700, height=500)
        self.feed_frame.pack(pady=10, fill="both", expand=True)
        self.load_feed()

    def load_feed(self):
        for widget in self.feed_frame.winfo_children():
            widget.destroy()
        try:
            resp = requests.get(f"{self.server_url}/feed", headers={"Authorization": f"Bearer {self.token}"})
            if resp.status_code == 200:
                posts = resp.json().get("posts", [])
                for post in posts:
                    self.display_post(post)
            else:
                messagebox.showerror("Error", resp.json().get("error", f"Failed to load feed ({resp.status_code})"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def display_post(self, post):
        frame = ctk.CTkFrame(self.feed_frame, corner_radius=10)
        frame.pack(pady=10, padx=10, fill="x")
        # Username display logic inspired by feed.html
        user = post.get("user")
        federated_from = post.get("federated_from")
        if user:
            if federated_from:
                user_display = f"{user}@{federated_from}"
            else:
                user_display = user
        else:
            user_display = "Unknown"
        title = ctk.CTkLabel(frame, text=post.get("title", ""), font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", padx=10, pady=(5, 0))
        meta = ctk.CTkLabel(frame, text=f"by {user_display}", font=("Segoe UI", 12, "italic"))
        meta.pack(anchor="w", padx=10)
        content = ctk.CTkLabel(frame, text=post.get("content", ""), font=("Segoe UI", 14))
        content.pack(anchor="w", padx=10, pady=(0, 5))
        # TODO: Add upvote, comment, and federated actions

    def show_new_post(self):
        win = ctk.CTkToplevel(self.parent)
        win.title("New Post")
        win.geometry("400x300")
        title_entry = ctk.CTkEntry(win, placeholder_text="Title")
        title_entry.pack(pady=10, fill="x", padx=20)
        content_entry = ctk.CTkTextbox(win, height=120)
        content_entry.pack(pady=10, fill="both", padx=20)
        def submit():
            title = title_entry.get()
            content = content_entry.get("1.0", "end").strip()
            try:
                resp = requests.post(f"{self.server_url}/post", json={"title": title, "content": content}, headers={"Authorization": f"Bearer {self.token}"})
                if resp.status_code == 200:
                    messagebox.showinfo("Success", "Post created!")
                    win.destroy()
                    self.load_feed()
                else:
                    messagebox.showerror("Error", resp.json().get("error", f"Failed to post ({resp.status_code})"))
            except Exception as e:
                messagebox.showerror("Error", str(e))
        submit_btn = ctk.CTkButton(win, text="Submit", command=submit)
        submit_btn.pack(pady=10)

class RSSXClient(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RSSX - Stylish Federated Social Client")
        self.geometry("1100x750")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.logo = ctk.CTkLabel(self.sidebar, text="RSSX", font=("Segoe UI", 28, "bold"))
        self.logo.pack(pady=(40, 20))
        self.add_tab_btn = ctk.CTkButton(self.sidebar, text="+ New Tab", command=self.add_tab)
        self.add_tab_btn.pack(pady=10, fill="x")
        self.logout_btn = ctk.CTkButton(self.sidebar, text="Close Tab", command=self.close_current_tab)
        self.logout_btn.pack(side="bottom", pady=20, fill="x")

        # Tabs bar
        self.tabs_bar = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.tabs_bar.pack(side="top", fill="x")
        self.tabs_area = ctk.CTkFrame(self, corner_radius=15)
        self.tabs_area.pack(side="left", fill="both", expand=True, padx=30, pady=30)

        self.tabs = []
        self.tab_buttons = []
        self.current_tab = None
        self.add_tab()

    def add_tab(self):
        server_url = simpledialog.askstring("Server URL", "Enter RSSX server API URL (e.g. http://localhost:5000/api):", parent=self)
        if not server_url:
            return
        tab = ServerTab(self, server_url)
        self.tabs.append(tab)
        btn = ctk.CTkButton(self.tabs_bar, text=server_url, command=lambda t=tab: self.switch_tab(t), width=180)
        btn.pack(side="left", padx=5, pady=5)
        self.tab_buttons.append(btn)
        self.switch_tab(tab)

    def switch_tab(self, tab):
        if self.current_tab:
            self.current_tab.frame.pack_forget()
        self.current_tab = tab
        tab.frame.pack(fill="both", expand=True)

    def close_current_tab(self):
        if not self.current_tab:
            return
        idx = self.tabs.index(self.current_tab)
        self.current_tab.frame.destroy()
        self.tab_buttons[idx].destroy()
        del self.tabs[idx]
        del self.tab_buttons[idx]
        self.current_tab = None
        if self.tabs:
            self.switch_tab(self.tabs[-1])

    def on_close(self):
        self.destroy()

if __name__ == "__main__":
    app = RSSXClient()
    app.mainloop()
