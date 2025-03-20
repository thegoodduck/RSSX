import requests
import json
import os

# Config File Path
CONF_FILE = 'conf.txt'


def load_server_preferences():
    """Load server preferences from the conf.txt file."""
    if os.path.exists(CONF_FILE):
        with open(CONF_FILE, 'r') as file:
            servers = [line.strip() for line in file.readlines()]
        return servers
    return []


def save_server_preferences(servers):
    """Save server preferences to the conf.txt file."""
    with open(CONF_FILE, 'w') as file:
        for server in servers:
            file.write(f"{server}\n")


def register_user(server_url):
    """Register the user with a specific server."""
    username = input("Enter your username: ")
    data = {"username": username}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/register", json=data, headers=headers)

    if response.status_code == 200:
        print(f"User registered successfully on {server_url}: {response.json()['message']}")
    else:
        print(f"Error on {server_url}: {response.json().get('error', 'Unknown error')}")


def create_post(server_url):
    """Create a new post on a specific server."""
    content = input("Enter post content: ")
    data = {"content": content}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/post", json=data, headers=headers)

    if response.status_code == 200:
        print(f"Post successfully saved on {server_url}: {response.json()['post_filename']}")
    else:
        print(f"Error on {server_url}: {response.json().get('error', 'Unknown error')}")


def view_post(server_url):
    """View a post by ID from a specific server."""
    post_id = input("Enter post ID to view: ")
    response = requests.get(f"{server_url}/post/{post_id}")

    if response.status_code == 200:
        post_data = response.json()
        post_content = post_data.get('post', '')

        if post_content:
            post_lines = post_content.split('\n')
            post_info = {line.split(": ")[0]: line.split(": ")[1] for line in post_lines if ": " in line}

            print("\n--- Post Details ---")
            print(f"Post ID: {post_info.get('ID', 'No ID found')}")
            print(f"Author: {post_info.get('Author', 'No author found')}")
            print(f"Content: {post_info.get('Content', 'No content available')}")
            print(f"Created At: {post_info.get('Timestamp', 'No timestamp available')}")
            print(f"Signature: {post_info.get('Signature', 'No signature found')}")
            print("--------------------\n")
        else:
            print("Post content not found")
    else:
        print(f"Error on {server_url}: {response.json().get('error', 'Post not found')}")


def get_feed(servers):
    """Get the RSS feed with post content from all servers."""
    for server_url in servers:
        print(f"\nFetching feed from {server_url}:")
        response = requests.get(f"{server_url}/feed")
        if response.status_code == 200:
            try:
                data = response.json()
                posts = data.get("posts", [])

                if not posts:
                    print("No posts available.")
                    return
                
                for post in posts:
                    print("----- POST -----")
                    lines = post.split("\n")
                    for line in lines:
                        print(line)
                    print("----------------\n")

            except json.JSONDecodeError:
                print("Failed to parse server response.")
        else:
            print(f"Error: {response.status_code}, {response.text}")

def add_server(servers):
    """Add a new server URL to the list of servers."""
    new_server = input("Enter the server URL to add: ")
    if new_server not in servers:
        servers.append(new_server)
        save_server_preferences(servers)
        print(f"Server {new_server} added successfully.")
    else:
        print(f"Server {new_server} is already in the list.")


def choose_server(servers):
    """Allow user to choose a specific server from the list."""
    if not servers:
        print("No servers available.")
        return None

    print("\nAvailable Servers:")
    for i, server in enumerate(servers, start=1):
        print(f"{i}. {server}")

    choice = input("Choose a server number (or press Enter to cancel): ")

    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(servers):
            return servers[index]
    print("Invalid choice.")
    return None


def main_menu(servers):
    """Main menu to navigate the client options."""
    while True:
        print("\nMenu:")
        print("1. Register user on all servers")
        print("2. Register user on a specific server")
        print("3. Create a new post on all servers")
        print("4. Create a new post on a specific server")
        print("5. View a post by ID from all servers")
        print("6. View feeds from all servers")
        print("7. Add a new server")
        print("8. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            for server_url in servers:
                register_user(server_url)
        elif choice == "2":
            server = choose_server(servers)
            if server:
                register_user(server)
        elif choice == "3":
            for server_url in servers:
                create_post(server_url)
        elif choice == "4":
            server = choose_server(servers)
            if server:
                create_post(server)
        elif choice == "5":
            for server_url in servers:
                view_post(server_url)
        elif choice == "6":
            get_feed(servers)
        elif choice == "7":
            add_server(servers)
        elif choice == "8":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    servers = load_server_preferences()

    if not servers:
        save_server_preferences([])
        print("No servers found. Please add servers to the configuration file (conf.txt).")
    else:
        main_menu(servers)


