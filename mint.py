#!/usr/bin/env python3
"""
mint.py — mint one NFT from each wallet by replaying a raw mint calldata
against an OpenSea SeaDrop-style minter contract on Base.

How the calldata was obtained: inspect any recent successful mint tx for
the collection on a block explorer / RPC, copy its input data. For
OpenSea's "Open Edition" mint the call goes to the shared minter contract
(MINTER) with selector 0x161ac21f (mintPublic), and the calldata is
identical for every minter (no per-wallet signature) — so it is replayable.

    decoded 0x161ac21f mintPublic(nftContract, feeRecipient, minterIfNotPayer, quantity):
      nftContract       = 0xe35b...  (the ERC721 being minted)
      feeRecipient      = 0x0000a26b... (OpenSea fee recipient)
      minterIfNotPayer  = 0x0           (mint to msg.sender)
      quantity          = 1

Usage:
    python mint.py wallets.txt \
        --minter 0x00005ea00ac477b1030ce78506496e8c2de24bf5 \
        --calldata 0x161ac21f...
"""
import argparse
import json
import time

from common import get_w3, load_wallets, suggested_gas_price, CHAIN_ID


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet_file")
    ap.add_argument("--minter", required=True, help="minter contract address")
    ap.add_argument("--calldata", required=True, help="raw mint calldata (0x...)")
    ap.add_argument("--value-wei", type=int, default=0, help="mint price per tx in wei")
    ap.add_argument("--gas", type=int, default=140000)
    ap.add_argument("--out", default="mint_results.json")
    args = ap.parse_args()

    w3 = get_w3()
    minter = w3.to_checksum_address(args.minter)
    rows = load_wallets(args.wallet_file)
    gp = suggested_gas_price(w3)

    results = []
    for i, (addr, priv) in enumerate(rows):
        a = w3.to_checksum_address(addr)
        h = None
        err = None
        try:
            nonce = w3.eth.get_transaction_count(a)
            tx = {
                "to": minter,
                "value": args.value_wei,
                "gas": args.gas,
                "maxFeePerGas": gp,
                "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
                "nonce": nonce,
                "chainId": CHAIN_ID,
                "type": 2,
                "data": args.calldata,
            }
            signed = w3.eth.account.sign_transaction(tx, priv)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
        except Exception as e:
            err = str(e)[:100]
        if h:
            results.append({"idx": i + 1, "addr": addr, "tx": h.hex(), "status": "sent"})
            print(f"#{i+1:>3} {addr} mint -> {h.hex()}")
        else:
            results.append({"idx": i + 1, "addr": addr, "tx": None, "status": "fail", "err": err})
            print(f"#{i+1:>3} {addr} FAIL: {err}")
        time.sleep(0.2)

    json.dump(results, open(args.out, "w"), indent=2)
    sent = sum(1 for r in results if r["status"] == "sent")
    print(f"\nMINT BROADCAST: {sent}/{len(rows)}")


if __name__ == "__main__":
    main()
