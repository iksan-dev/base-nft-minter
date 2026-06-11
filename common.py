#!/usr/bin/env python3
"""
common.py — shared helpers for the Base mint/transfer/sweep scripts.
"""
import time

from web3 import Web3

BASE_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453

# OpenSea SeaDrop-style shared minter contract on Base.
OPENSEA_MINTER = "0x00005ea00ac477b1030ce78506496e8c2de24bf5"
# OpenSea fee recipient used by mintPublic on Base.
OPENSEA_FEE_RECIPIENT = "0x0000a26b00c1f0df003000390027140000faa719"
# mintPublic(address nftContract, address feeRecipient,
#            address minterIfNotPayer, uint256 quantity)
MINT_PUBLIC_SELECTOR = "0x161ac21f"


def get_w3() -> Web3:
    return Web3(Web3.HTTPProvider(BASE_RPC))


def _addr_word(addr: str) -> str:
    """Left-pad a 20-byte address to a 32-byte ABI word (no 0x)."""
    return addr.lower().replace("0x", "").rjust(64, "0")


def _uint_word(n: int) -> str:
    return hex(n)[2:].rjust(64, "0")


def build_mint_public_calldata(
    nft_contract: str,
    quantity: int = 1,
    fee_recipient: str = OPENSEA_FEE_RECIPIENT,
    minter_if_not_payer: str = "0x0000000000000000000000000000000000000000",
) -> str:
    """Build OpenSea mintPublic calldata for a given NFT contract.

    The call carries no per-wallet signature, so the same calldata is
    replayable from every wallet. minter_if_not_payer = 0x0 means "mint to
    msg.sender" (the wallet that signs/sends the tx).
    """
    return (
        MINT_PUBLIC_SELECTOR
        + _addr_word(nft_contract)
        + _addr_word(fee_recipient)
        + _addr_word(minter_if_not_payer)
        + _uint_word(quantity)
    )


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
