#!/usr/bin/env python3
"""
generate_wallets.py — generate N fresh EVM keypairs.

Output: a text file with one "address | privatekey" per line.

WARNING: the output file contains PRIVATE KEYS in plaintext. Keep it
chmod 600 and never commit it (see .gitignore).

Usage:
    python generate_wallets.py 100 wallets.txt
"""
import sys
import os
import secrets

from eth_account import Account


def generate(count: int, out_path: str) -> None:
    lines = []
    for _ in range(count):
        priv = "0x" + secrets.token_hex(32)
        acct = Account.from_key(priv)
        lines.append(f"{acct.address} | {priv}")

    with open(out_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(out_path, 0o600)
    print(f"Saved {len(lines)} wallets to {out_path} (chmod 600)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    out = sys.argv[2] if len(sys.argv) > 2 else "wallets.txt"
    generate(n, out)
