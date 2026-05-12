import os
import json
import hashlib
import random
import getpass
import datetime
import string
import pyperclip
from colorama import Fore, Back, Style, init
from cryptography.fernet import Fernet

init(autoreset=True)

VAULT_FILE = "vault.json"
KEY_FILE = "secret.key"

PINK = "\033[95m"
PURPLE = "\033[94m"
LIGHT_PURPLE = "\033[35m"
RESET = "\033[0m"

def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    with open(KEY_FILE, "rb") as f:
        return f.read()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_vault():
    if not os.path.exists(VAULT_FILE):
        return {"master": None, "passwords": {}}
    with open(VAULT_FILE, "r") as f:
        return json.load(f)

def save_vault(vault):
    with open(VAULT_FILE, "w") as f:
        json.dump(vault, f, indent=2)

def generate_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(random.choices(chars, k=length))

def check_strength(password):
    score = 0
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()" for c in password):
        score += 1

    if score <= 2:
        return PINK + "Weak — you can do better than that"
    elif score <= 4:
        return LIGHT_PURPLE + "Medium — getting there"
    else:
        return PURPLE + "Strong — nice"

def setup_master(vault):
    print(PINK + "Looks like your first time here. Set a master password:")
    master = getpass.getpass(PURPLE + "Master password: " + RESET)
    vault["master"] = hash_password(master)
    save_vault(vault)
    print(PINK + "You're all set.\n")

def verify_master(vault):
    attempts = 3
    while attempts > 0:
        attempt = getpass.getpass(PURPLE + "Master password: " + RESET)
        if hash_password(attempt) == vault["master"]:
            return True
        attempts -= 1
        if attempts > 0:
            print(PINK + f"Incorrect. {attempts} attempt{'s' if attempts > 1 else ''} left.")
        else:
            print(PINK + "Too many incorrect attempts. Closing.")
    return False

def add_password(vault, fernet):
    site = input(PINK + "Site name: " + RESET)
    
    if site in vault["passwords"]:
        print(LIGHT_PURPLE + f"{site} already exists in your vault.")
        print(PINK + "\n[1] Update it  [2] View it  [3] Cancel")
        action = input(PURPLE + "> " + RESET).strip()
        
        if action == "2":
            entry = vault["passwords"][site]
            decrypted = fernet.decrypt(entry["password"].encode()).decode()
            print(PURPLE + f"\nUsername: {entry['username']}")
            print(PURPLE + f"Password: {decrypted}")
            pyperclip.copy(decrypted)
            print(PINK + "Copied to clipboard.")
            return
        elif action == "3":
            print(PINK + "Cancelled.")
            return
        elif action != "1":
            print(LIGHT_PURPLE + "Invalid choice, cancelling.")
            return

        print(LIGHT_PURPLE + "Updating — leave a field blank to keep it the same.")
        old = vault["passwords"][site]
        old_decrypted = fernet.decrypt(old["password"].encode()).decode()

        new_username = input(PINK + f"Username or email [{old['username']}]: " + RESET)
        if not new_username:
            new_username = old["username"]

        print(PINK + "New password (or hit Enter to keep current): " + RESET, end="")
        new_password = input()

        if not new_password:
            print(PURPLE + "Kept existing password.")
            vault["passwords"][site]["username"] = new_username
            save_vault(vault)
            print(PURPLE + f"Updated {site}.")
            return

        if "history" not in vault["passwords"][site]:
            vault["passwords"][site]["history"] = []
        vault["passwords"][site]["history"].append({
            "password": old["password"],
            "saved_on": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        strength = check_strength(new_password)
        print(f"Strength: {strength}")

        encrypted = fernet.encrypt(new_password.encode()).decode()
        vault["passwords"][site]["username"] = new_username
        vault["passwords"][site]["password"] = encrypted
        save_vault(vault)
        print(PURPLE + f"Updated {site}.")
        return

    username = input(PINK + "Username or email: " + RESET)
    print(PINK + "Password (or just hit Enter and I'll generate one): " + RESET, end="")
    password = input()

    if not password:
        password = generate_password()
        print(PURPLE + f"Generated: {password}")
        pyperclip.copy(password)
        print(PINK + "Copied to clipboard — you're good.")

    strength = check_strength(password)
    print(f"Strength: {strength}")

    encrypted = fernet.encrypt(password.encode()).decode()
    vault["passwords"][site] = {"username": username, "password": encrypted, "history": []}
    save_vault(vault)
    print(PURPLE + f"Saved {site}.")


def view_history(vault, fernet):
    site = input(PINK + "Which site? " + RESET)
    if site not in vault["passwords"]:
        print(LIGHT_PURPLE + "Couldn't find that one.")
        return
    history = vault["passwords"][site].get("history", [])
    if not history:
        print(LIGHT_PURPLE + "No history yet for that site.")
        return
    print(PURPLE + f"\nPassword history for {site}:")
    for entry in history:
        decrypted = fernet.decrypt(entry["password"].encode()).decode()
        print(PINK + f"  {entry['saved_on']} — {decrypted}")


def get_password(vault, fernet):
    query = input(PINK + "Site name or search: " + RESET).lower()
    matches = [s for s in vault["passwords"] if query in s.lower()]

    if not matches:
        print(LIGHT_PURPLE + "Nothing found for that.")
        return

    if len(matches) > 1:
        print(PURPLE + "Found a few matches:")
        for i, s in enumerate(matches):
            print(f"  [{i+1}] {s}")
        choice = int(input(PINK + "Which one? " + RESET)) - 1
        site = matches[choice]
    else:
        site = matches[0]

    entry = vault["passwords"][site]
    decrypted = fernet.decrypt(entry["password"].encode()).decode()
    print(PURPLE + f"\nUsername: {entry['username']}")
    print(PURPLE + f"Password: {decrypted}")
    pyperclip.copy(decrypted)
    print(PINK + "Copied to clipboard.\n")

def delete_password(vault):
    site = input(PINK + "Which site do you want to remove? " + RESET)
    if site not in vault["passwords"]:
        print(LIGHT_PURPLE + "Couldn't find that one.")
        return
    confirm = input(LIGHT_PURPLE + f"Are you sure you want to remove {site}? (y/n): " + RESET)
    if confirm.lower() == "y":
        del vault["passwords"][site]
        save_vault(vault)
        print(PURPLE + f"Removed {site}.")
    else:
        print(PINK + "Cancelled.")

def list_sites(vault):
    if not vault["passwords"]:
        print(LIGHT_PURPLE + "Nothing saved yet.")
        return
    print(PURPLE + "\nHere's what you've got:")
    for site, data in vault["passwords"].items():
        print(PINK + f"  {site} — {data['username']}")

def export_vault(vault, fernet):
    filename = input(PINK + "Export filename (e.g. backup.txt): " + RESET)
    if not filename:
        print(LIGHT_PURPLE + "No filename entered, cancelling.")
        return
    with open(filename, "w") as f:
        f.write(f"ZW Vault Export — Zach Wenger\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("-" * 40 + "\n")
        for site, data in vault["passwords"].items():
            decrypted = fernet.decrypt(data["password"].encode()).decode()
            f.write(f"{site} | {data['username']} | {decrypted}\n")

def main():
    fernet = Fernet(load_key())
    vault = load_vault()

    print(PINK + Style.BRIGHT + "\n=== ZW Vault — by Zach Wenger ===\n" + RESET)

    if not vault["master"]:
        setup_master(vault)

    print(PURPLE + "Hey, welcome back. Enter your master password to get in:")
    if not verify_master(vault):
        return

    print(PURPLE + "\nYou're in.")
    while True:
        print(PINK + "\n[1] Add  [2] Get  [3] List  [4] Remove  [5] History  [6] Export  [7] Quit")
        choice = input(PURPLE + "> " + RESET).strip()
        if choice == "1":
            add_password(vault, fernet)
        elif choice == "2":
            get_password(vault, fernet)
        elif choice == "3":
            list_sites(vault)
        elif choice == "4":
            delete_password(vault)
        elif choice == "5":
            view_history(vault, fernet)
        elif choice == "6":
            export_vault(vault, fernet)
        elif choice == "7":
            print(PINK + "Later.")
            print(LIGHT_PURPLE + "  github.com/zachwenger")
            break

if __name__ == "__main__":
    main()