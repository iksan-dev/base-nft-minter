# base-nft-minter

Reusable multi-wallet NFT mint pipeline for **Base**, done entirely through
raw contract calls — no marketplace UI, no browser automation.

Point it at any OpenSea-style `mintPublic` drop by **contract address** and
it will: generate fresh wallets, fund them, mint one NFT from each, gather
every NFT into a single collector wallet, then sweep the leftover ETH back.

## Why this exists

Most "mint pages" are just a button that calls a contract. This repo skips
the page and calls the contract directly from N wallets in parallel, so you
can mint a whole drop programmatically and consolidate the results.

It is **generic over the target drop** — you select the NFT contract; the
mint calldata is built for you. For non-OpenSea contracts you can supply
raw calldata instead.

## How the mint works

By default this targets OpenSea's shared SeaDrop-style minter contract on
Base via `mintPublic` (selector `0x161ac21f`). The call carries no
per-wallet signature, so the **same calldata is replayable from every
wallet**:

```
mintPublic(nftContract, feeRecipient, minterIfNotPayer, quantity)
  nftContract      = the ERC721 being minted   <- you choose this
  feeRecipient     = OpenSea fee recipient      (default baked in)
  minterIfNotPayer = 0x0  -> mint to msg.sender
  quantity         = 1                          (--quantity to change)
```

`mint.py` builds this for you via `build_mint_public_calldata()` in
`common.py`. You only select the target contract:

```bash
python mint.py wallets.txt --nft 0xNFT_CONTRACT
```

**Non-OpenSea / custom drops:** open any recent successful mint tx for that
collection on a block explorer, copy its raw input data, and pass it via
`--minter 0x... --calldata 0x...`. Everything else (fund, gather, sweep)
works unchanged.

## Pipeline

```bash
pip install -r requirements.txt

# 1. generate N wallets  (output file holds PLAINTEXT private keys — keep it safe)
python generate_wallets.py 100 wallets.txt

# 2. fund each wallet (amount in wei; here ~$0.02 of ETH)
#    funder = line #1 of the funder file
python fund.py wallets.txt --amount-wei 12094274872632 --funder-file funder.txt

# 3. mint one NFT from each wallet — just select the target NFT contract
python mint.py wallets.txt --nft 0xNFT_CONTRACT
#    (non-OpenSea drop: --minter 0x... --calldata 0x... instead)

# 4. gather every NFT into one collector
python transfer.py wallets.txt mint_results.json \
    --nft 0xNFT_CONTRACT \
    --to 0xYOUR_COLLECTOR

# 5. sweep leftover ETH back to the collector
python sweep.py wallets.txt --to 0xYOUR_COLLECTOR
```

## Configuration

| What | Where |
|------|-------|
| RPC endpoint | `BASE_RPC` in `common.py` (swap for a private RPC on big batches) |
| Chain id | `CHAIN_ID` in `common.py` (8453 = Base mainnet) |
| OpenSea minter / fee recipient | `OPENSEA_MINTER`, `OPENSEA_FEE_RECIPIENT` in `common.py` |
| Mint quantity per wallet | `--quantity` on `mint.py` |
| Mint price (paid mints) | `--value-wei` on `mint.py` |

Targeting another EVM chain: change `BASE_RPC` + `CHAIN_ID`, and supply
that chain's minter/calldata.

## Notes & gotchas

- **Public RPC throttles hard** under load. `common.rpc_retry` retries with
  backoff; for large batches use a private RPC.
- **Sweep gas reserve uses a 2x buffer.** The node validates
  `gas * maxFeePerGas + value <= balance`. Leaving zero headroom triggers
  `insufficient funds for gas * price + value`. Leftover dust per wallet is
  not economical to withdraw.
- **TokenIds** are read from each mint tx's `Transfer(from=0x0)` log, so this
  works even when the contract is not `ERC721Enumerable`.

## Security

- The wallet file contains **plaintext private keys**. It is `chmod 600` on
  creation and is git-ignored. **Never commit it.**
- This repo ships only the tooling, never keys or run artifacts
  (`*_results.json`, `*.log` are ignored).
- Mint responsibly: respect per-wallet limits and the terms of the drops you
  interact with.

## License

MIT
