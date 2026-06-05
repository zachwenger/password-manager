# `● ZW Vault — Password Manager`

**Local-first Python password manager. AES-128 encryption (Fernet), SHA-256 master-password hashing, lockout after 3 wrong attempts, password history, secure clipboard handoff.**

Built to actually understand how password managers work under the hood, not just use one. Every component (encryption at rest, hashing, key management, brute-force defense) was implemented to learn the underlying primitive — then re-evaluated against what production tools like Bitwarden, 1Password, and KeePass do differently.

By Zach Wenger · [github.com/zachwenger](https://github.com/zachwenger)

![Demo](demo.gif)

---

## What it does

| Feature | How it works |
|---|---|
| **Add credentials** | Encrypts the password with Fernet (AES-128 CBC + HMAC-SHA256) before writing to `vault.json` |
| **Master password** | SHA-256 hash stored, never the plaintext |
| **Password generator** | Configurable length, cryptographic randomness via `random.choices` over alphanumeric + symbols |
| **Strength checker** | Scores length + class diversity, flags weak / medium / strong |
| **Hidden input** | `getpass` keeps the master and new passwords off the terminal display |
| **Brute force protection** | 3 attempts, then process exits |
| **Clipboard handoff** | Passwords copy via `pyperclip`, never displayed on screen unless you explicitly ask |
| **Fuzzy site search** | Substring match across all stored sites |
| **Password history** | Old passwords retained on update, timestamped, encrypted |
| **Delete confirmation** | `y/n` prompt before removal |
| **Plaintext export** | Optional, timestamped, for migration to a real tool |

---

## Threat model

What this defends against — and what it doesn't.

### Defends against

- **Cold-storage disclosure of `vault.json`** — values are AES-encrypted, useless without `secret.key`
- **Master-password disclosure of the hash** — SHA-256 of master means even an attacker reading `vault.json` can't directly recover the master
- **Brute-force at the prompt** — 3-attempt lockout makes online guessing infeasible
- **Shoulder surfing the master password** — `getpass` hides input
- **Accidental display of stored passwords** — clipboard-only output by default

### Does NOT defend against

These are the real-world threats. **If any of these matter to you, use Bitwarden or 1Password, not this.**

| Threat | Why this is vulnerable | What production tools do |
|---|---|---|
| Stolen device with both `vault.json` + `secret.key` | Key is stored alongside the vault — full decryption possible | Key derived from master via PBKDF2/Argon2id, never stored at rest |
| Memory dump while running | Plaintext passwords live in process memory unencrypted | Same — but production tools clear memory aggressively + use OS keychains |
| Keylogger | Master password captured at the prompt | Same — no software defense, only hardware tokens / passkeys |
| Offline brute force of the master | SHA-256 is fast — attackers GPU-crack billions/sec | PBKDF2/Argon2id with high iteration count makes this infeasible |
| Clipboard sniffer | Passwords sit in clipboard until next copy | 1Password / Bitwarden auto-clear clipboard after 30s |
| Anyone with the same device unlocked | No re-auth on idle | Production tools require re-auth after idle timeout |
| Plaintext export file | Written unencrypted to disk | Same — but production tools warn loudly and require confirmation |

**Honest summary:** this is a *learning project*, not a security product. The cryptography is correct in isolation, but the system-level design has gaps a real attacker would walk through. I'd recommend Bitwarden (open-source, audited, properly hardened) for actual use.

---

## What I'd change for v2

A proper crypto upgrade path that would close the gaps above:

1. **Derive the encryption key from the master with Argon2id**, not store it on disk. `secret.key` shouldn't exist as a file — it should be regenerated each session from the master + a salt.
2. **Replace SHA-256 master hash with Argon2id** too. Same primitive, applied to authentication. Slow-by-design hash makes offline brute force infeasible.
3. **Clipboard auto-clear timer** — clear after 30s.
4. **Idle timeout** — re-prompt for the master after N minutes of inactivity.
5. **Encrypted export** — `.age` or `.gpg` only, never plaintext.
6. **Audit log** — every read/write tagged with timestamp + action, kept inside the encrypted vault.

This is on the v2 list. Not built yet because the point of v1 was to learn the *building blocks*, not ship a competitive product.

---

## How to run it

```bash
git clone https://github.com/zachwenger/password-manager
cd password-manager
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS / Linux
pip install cryptography pyperclip colorama
python manager.py
```

First run prompts for a master password. Subsequent runs prompt to verify it.

> Run this on test data only. Don't put your real credentials in v1 — see threat model above.

---

## File structure

```
password-manager/
├── manager.py          — full CLI app
├── vault.json          — encrypted vault (gitignored)
├── secret.key          — Fernet symmetric key (gitignored)
├── demo.gif            — terminal recording of the CLI
├── README.md           — this file
└── .gitignore
```

`vault.json` and `secret.key` are created on first run and never tracked
by git — both are listed in `.gitignore`.

---

## Stack

| | |
|---|---|
| Language | Python 3 |
| Encryption | `cryptography.fernet` (AES-128-CBC + HMAC-SHA256) |
| Hashing | `hashlib.sha256` (v1; Argon2id planned for v2) |
| Secure input | `getpass` |
| Clipboard | `pyperclip` |
| Terminal styling | `colorama` |
| Storage | Local `vault.json` only — no network, no cloud |

---

## Security concepts I picked up building this

- **Encryption vs hashing** — when to use each, why master passwords are hashed but stored credentials are encrypted (encryption is reversible with a key, hashing isn't)
- **AES symmetric encryption + the operating modes** — Fernet wraps AES-128-CBC with HMAC for authenticity, prevents tampering
- **Why fast hashes are dangerous for passwords** — SHA-256 is built for speed, which is exactly wrong for password storage; PBKDF2 / Argon2 are slow by design
- **The key management problem** — solving "how do we keep the key safe" recursively (this is why production tools derive keys from the master instead of storing them)
- **Brute force economics** — why 3 attempts + lockout works for online attacks but does nothing against offline hash cracking
- **Clipboard as an attack surface** — passwords sit in OS clipboard memory until overwritten, accessible to any process running as the same user
- **Defense in depth** — no single control should be load-bearing; the whole stack matters

---

## What this taught me

Building the wrong version of something is how you understand the right version. I now know exactly why production password managers spend so much effort on key derivation, clipboard hygiene, idle timeouts, and memory zeroization — because I built the version *without* those things and can see clearly where it breaks.

The hardest part was getting key management right so the vault survives close-and-reopen cycles. The interesting part was realizing that's *exactly the problem* every real-world password manager solves with a different (better) tradeoff than I made here.

If anyone copies this for actual use: don't. Use Bitwarden. This was a learning exercise. If you copy it for your own learning exercise: 1) ship v2, 2) read the threat model honestly, 3) keep going.

---

*Code is mine. The cryptography is implemented from documented standards (Fernet spec, SHA-256 NIST FIPS 180-4). No proprietary algorithms.*
