#!/usr/bin/env python3
"""
common.py — shared helpers for the Base mint/transfer/sweep scripts.
"""
import time

from web3 import Web3

BASE_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453


def get_w3() -> Web3:
    return Web3(Web3.HTTPProvider(BASE_RPC))


def load_wallets(path: str):
    """Return list of (address, private_key) tuples."""
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            addr, priv = line.split(" | ")
            rows.append((addr, priv))
    return rows


def rpc_retry(fn, attempts: int = 8, delay: float = 1.5, default=None):
    """Public RPCs throttle hard under load; retry with backoff."""
    for _ in range(attempts):
        try:
            return fn()
        except Exception:
            time.sleep(delay)
    return default


def suggested_gas_price(w3: Web3) -> int:
    """A padded EIP-1559 maxFeePerGas. Base gas is tiny but spikes; 3x + buffer."""
    base = rpc_retry(lambda: w3.eth.gas_price)
    return int(base * 3) + w3.to_wei(0.05, "gwei")
