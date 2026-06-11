#!/usr/bin/env python3
"""
transfer.py — move each freshly minted NFT to a single collector address.

For each wallet we read its mint tx receipt, extract the minted tokenId
from the ERC721 Transfer(from=0x0) log, then call safeTransferFrom to send
that token to the collector.

Usage:
    python transfer.py wallets.txt mint_results.json \
        --nft 0xe35b7e37c125abeee67809d89173dd03e473e3a4 \
        --to 0xCOLLECTOR...
"""
import argparse
import json
import time

from common import get_w3, load_wallets, suggested_gas_price, CHAIN_ID, rpc_retry

SAFE_TRANSFER_SEL = "0x42842e0e"  # safeTransferFrom(address,address,uint256)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet_file")
    ap.add_argument("mint_results", help="mint_results.json from mint.py")
    ap.add_argument("--nft", required=True, help="ERC721 contract address")
    ap.add_argument("--to", required=True, help="collector address")
    ap.add_argument("--gas", type=int, default=120000)
    ap.add_argument("--out", default="transfer_results.json")
    args = ap.parse_args()

    w3 = get_w3()
    nft = w3.to_checksum_address(args.nft)
    collector = w3.to_checksum_address(args.to)
    transfer_sig = w3.keccak(text="Transfer(address,address,uint256)").hex().lower().replace("0x", "")

    priv_map = {a.lower(): p for a, p in load_wallets(args.wallet_file)}
    mint = json.load(open(args.mint_results))
    txmap = {
        r["addr"].lower(): (r["tx"] if r["tx"].startswith("0x") else "0x" + r["tx"])
        for r in mint if r["status"] == "sent"
    }

    def get_tokenid(txhash):
        def _():
            rc = w3.eth.get_transaction_receipt(txhash)
            for log in rc.logs:
                if (log["address"].lower() == nft.lower()
                        and log["topics"][0].hex().lower().replace("0x", "") == transfer_sig):
                    return int(log["topics"][3].hex(), 16)
            return None
        return rpc_retry(_)

    def calldata(frm, to, tid):
        return (SAFE_TRANSFER_SEL
                + frm[2:].rjust(64, "0").lower()
                + to[2:].rjust(64, "0").lower()
                + hex(tid)[2:].rjust(64, "0"))

    gp = suggested_gas_price(w3)
    results = []
    for addr_lc, txh in txmap.items():
        addr = w3.to_checksum_address(addr_lc)
        priv = priv_map[addr_lc]
        tid = get_tokenid(txh)
        if tid is None:
            results.append({"addr": addr, "tokenId": None, "status": "no_tokenid"})
            print(f"{addr} NO TOKENID")
            continue
        data = calldata(addr, collector, tid)
        h = None
        err = None
        try:
            nonce = w3.eth.get_transaction_count(addr)
            tx = {
                "to": nft, "value": 0, "gas": args.gas, "maxFeePerGas": gp,
                "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"), "nonce": nonce,
                "chainId": CHAIN_ID, "type": 2, "data": data,
            }
            signed = w3.eth.account.sign_transaction(tx, priv)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
        except Exception as e:
            err = str(e)[:100]
        if h:
            results.append({"addr": addr, "tokenId": tid, "tx": h.hex(), "status": "sent"})
            print(f"{addr} token {tid} -> {h.hex()}")
        else:
            results.append({"addr": addr, "tokenId": tid, "tx": None, "status": "fail", "err": err})
            print(f"{addr} token {tid} FAIL: {err}")
        time.sleep(0.4)

    json.dump(results, open(args.out, "w"), indent=2)
    sent = sum(1 for r in results if r["status"] == "sent")
    print(f"\nTRANSFER BROADCAST: {sent}/{len(txmap)}")


if __name__ == "__main__":
    main()
