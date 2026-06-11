#!/usr/bin/env python3
"""
fund.py — distribute a fixed ETH amount from a funder wallet to every
address in a wallet file (one funding tx per recipient).

The funder is line #1 of the wallet file; recipients are the rest (or
pass --all to fund every line, including #1's peers from another file).

Usage:
    python fund.py wallets.txt --amount-wei 12094274872632
"""
import argparse
import json
import time

from common import get_w3, load_wallets, suggested_gas_price, CHAIN_ID, rpc_retry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet_file")
    ap.add_argument("--amount-wei", type=int, required=True,
                    help="amount to send to each recipient, in wei")
    ap.add_argument("--funder-file", default=None,
                    help="file whose line #1 is the funder (defaults to wallet_file)")
    ap.add_argument("--out", default="fund_results.json")
    args = ap.parse_args()

    w3 = get_w3()
    funder_rows = load_wallets(args.funder_file or args.wallet_file)
    funder_addr, funder_priv = funder_rows[0]
    funder_addr = w3.to_checksum_address(funder_addr)

    recipients = [a for a, _ in load_wallets(args.wallet_file)]

    gp = suggested_gas_price(w3)
    nonce = rpc_retry(lambda: w3.eth.get_transaction_count(funder_addr))

    results = []
    for i, to in enumerate(recipients):
        tx = {
            "to": w3.to_checksum_address(to),
            "value": args.amount_wei,
            "gas": 21000,
            "maxFeePerGas": gp,
            "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "type": 2,
        }
        signed = w3.eth.account.sign_transaction(tx, funder_priv)
        try:
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            results.append({"idx": i + 1, "to": to, "tx": h.hex(), "status": "sent"})
            print(f"#{i+1:>3} {to} -> {h.hex()}")
            nonce += 1
        except Exception as e:
            results.append({"idx": i + 1, "to": to, "tx": None, "status": str(e)[:100]})
            print(f"#{i+1:>3} {to} ERR: {str(e)[:80]}")
        time.sleep(0.15)

    json.dump(results, open(args.out, "w"), indent=2)
    sent = sum(1 for r in results if r["status"] == "sent")
    print(f"\nFUNDED: {sent}/{len(recipients)}")


if __name__ == "__main__":
    main()
