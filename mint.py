#!/usr/bin/env python3
"""
mint.py — mint one NFT from each wallet on Base.

By default this targets OpenSea's shared SeaDrop-style minter and builds
the mintPublic calldata for you — you only need to select the target NFT
contract:

    python mint.py wallets.txt --nft 0xNFT_CONTRACT

mintPublic carries no per-wallet signature, so the same calldata is
replayable from every wallet. minterIfNotPayer is 0x0, meaning each NFT is
minted to the wallet that sends the tx.

Advanced overrides:
    --minter      minter contract (default: OpenSea Base minter)
    --quantity    quantity per wallet (default: 1)
    --calldata    supply raw calldata directly and skip the builder
                  (use this for non-OpenSea drops; copy the input data
                  from any recent successful mint tx of that collection)
    --value-wei   mint price per tx in wei (default: 0)

Examples:
    # OpenSea drop — just pick the contract
    python mint.py wallets.txt --nft 0xe35b7e37c125abeee67809d89173dd03e473e3a4

    # Non-OpenSea drop — replay raw calldata
    python mint.py wallets.txt --minter 0xMINTER --calldata 0xabcd...
"""
import argparse
import json
import time

from common import (
    get_w3,
    load_wallets,
    suggested_gas_price,
    build_mint_public_calldata,
    OPENSEA_MINTER,
    CHAIN_ID,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet_file")
    ap.add_argument("--nft", help="target NFT contract (calldata auto-built for OpenSea mintPublic)")
    ap.add_argument("--minter", default=OPENSEA_MINTER, help="minter contract address")
    ap.add_argument("--quantity", type=int, default=1, help="quantity to mint per wallet")
    ap.add_argument("--calldata", help="raw mint calldata override (skips the builder)")
    ap.add_argument("--value-wei", type=int, default=0, help="mint price per tx in wei")
    ap.add_argument("--gas", type=int, default=140000)
    ap.add_argument("--out", default="mint_results.json")
    args = ap.parse_args()

    if not args.calldata and not args.nft:
        ap.error("provide --nft (auto-build calldata) or --calldata (raw override)")

    w3 = get_w3()
    minter = w3.to_checksum_address(args.minter)
    calldata = args.calldata or build_mint_public_calldata(args.nft, quantity=args.quantity)
    print(f"minter   : {minter}")
    print(f"calldata : {calldata}")
    print(f"target   : {args.nft or '(raw calldata)'}\n")

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
                "data": calldata,
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
