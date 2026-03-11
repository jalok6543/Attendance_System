"""Reset user passwords. Run: python -m scripts.reset_passwords"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt


def main():
    password = "Password123!"
    h = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    print("Password:", password)
    print()
    print("Run this in Supabase SQL Editor:")
    print()
    print(
        f"UPDATE users SET password_hash = '{h}' "
        "WHERE email IN ('admin@school.com', 'teacher@school.com', 'student@school.com');"
    )


if __name__ == "__main__":
    main()
