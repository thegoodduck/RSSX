import requests
import json

# Server URL
server_url = input('Enter the server URL (e.g., http://localhost:5000): ')

def register_user():
    """Register the user with the server."""
    username = input("Enter your username: ")
    data = {
        "username": username
    }

    # Send POST request to register the user
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/register", json=data, headers=headers)

    # Check if the registration was successful
    if response.status_code == 200:
        print(f"User registered successfully: {response.json()['message']}")
    else:
        print(f"Error: {response.json().get('error', 'Unknown error')}")

def create_post():
    """Create a new post."""
    content = input("Enter post content: ")
    data = {
        "content": content
    }

    # Send POST request to create the post
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{server_url}/post", json=data, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        print(f"Post successfully saved: {response.json()['post_filename']}")
    else:
        print(f"Error: {response.json().get('error', 'Unknown error')}")

def view_post():
    # Input post ID to view
    post_id = input("Enter post ID to view: ")
    response = requests.get(f"{server_url}/post/{post_id}")

    # Check if the request was successful
    if response.status_code == 200:
        post_data = response.json()
        post_content = post_data.get('post', '')

        if post_content:
            # Split the post content into lines
            post_lines = post_content.split('\n')
            post_info = {line.split(": ")[0]: line.split(": ")[1] for line in post_lines if ": " in line}

            # Now you can access fields like 'ID', 'Author', 'Content', etc.
            post_id = post_info.get("ID", "No ID found")
            author = post_info.get("Author", "No author found")
            content = post_info.get("Content", "No content available")
            timestamp = post_info.get("Timestamp", "No timestamp available")
            signature = post_info.get("Signature", "No signature found")

            print(f"Post ID: {post_id}")
            print(f"Author: {author}")
            print(f"Content: {content}")
            print(f"Created At: {timestamp}")
            print(f"Signature: {signature}")
        else:
            print("Post content not found")
    else:
        print(f"Error: {response.json().get('error', 'Post not found')}")

def main_menu():
    """Main menu to navigate the client options."""
    # Register user at the beginning
    register_user()

    while True:
        print("\nMenu:")
        print("1. Create a new post")
        print("2. View a post by ID")
        print("3. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            create_post()
        elif choice == "2":
            view_post()
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
