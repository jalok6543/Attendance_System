"""Seed sample data for development. Run: python -m scripts.seed_data"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.hash import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


if __name__ == "__main__":
    # Generate hashes for default password "Password123!"
    print("Password hashes for 'Password123!':")
    print(hash_password("Password123!"))
