# worldcups-minter

Programmatic multi-wallet NFT minting on **Base**, done entirely through
raw contract calls — no marketplace UI, no browser automation.

The pipeline generates fresh wallets, funds them, mints one NFT each by
replaying a SeaDrop-style `mintPublic` calldata, gathers every NFT into a
single collector wallet, then sweeps the leftover ETH back.

> Built against the "World Cups" open-edition drop (OpenSea, Base), but the
> scripts are generic — pass any minter contract + calldata.

## How the mint works

Minting goes directly to OpenSea's shared minter contract via
`mintPublic` (selector `0x161ac21f`). Because the call carries no
per-wallet signature, the **same calldata is replayable from every
wallet**:

```
mintPublic(nftContract, feeRecipient, minterIfNotPayer, quantity)
  nftContract      = the ERC721 being minted
  feeRecipient     = OpenSea fee recipient
  minterIfNotPayer = 0x0  -> mint to msg.sender
  quantity         = 1
```

To mint, you only **select the target NFT contract** — `mint.py` builds
the calldata for you via `build_mint_public_calldata()` in `common.py`:

```bash
python mint.py wallets.txt --nft 0xNFT_CONTRACT
```

For a **non-OpenSea drop**, skip the builder: open any recent successful
mint tx for that collection on a block explorer, copy its raw input data,
and pass it via `--minter 0x... --calldata 0x...`.

## Pipeline

```bash
pip install -r requirements.txt

# 1. generate N wallets  (output file holds PLAINTEXT private keys — keep it safe)
python generate_wallets.py 100 wallets.txt

# 2. fund each wallet (here: ~$0.02 worth of ETH = 12094274872632 wei)
#    funder = line #1 of the funder file
python fund.py wallets.txt --amount-wei 12094274872632 --funder-file funder.txt

# 3. mint one NFT from each wallet — just select the target NFT contract
python mint.py wallets.txt --nft 0xe35b7e37c125abeee67809d89173dd03e473e3a4
#    (calldata is auto-built for OpenSea's mintPublic; for a non-OpenSea
#     drop, pass --minter 0x... --calldata 0x... instead)

# 4. gather every NFT into one collector
python transfer.py wallets.txt mint_results.json \
    --nft 0xe35b7e37c125abeee67809d89173dd03e473e3a4 \
    --to 0xYOUR_COLLECTOR

# 5. sweep leftover ETH back to the collector
python sweep.py wallets.txt --to 0xYOUR_COLLECTOR
```

## Notes & gotchas

- **Public Base RPC throttles hard** under load. `common.rpc_retry`
  retries with backoff; for large batches consider a private RPC.
- **Sweep gas reserve uses a 2x buffer.** The node validates
  `gas * maxFeePerGas + value <= balance`. Leaving zero headroom triggers
  `insufficient funds for gas * price + value`. The leftover dust per
  wallet is not economical to withdraw.
- **TokenIds** are read from each mint tx's `Transfer(from=0x0)` log, since
  this contract is not `ERC721Enumerable`.

## Security

- The wallet file contains **plaintext private keys**. It is `chmod 600`
  on creation and is git-ignored. **Never commit it.**
- This repo ships only the tooling, never keys or run artifacts
  (`*_results.json`, `*.log` are ignored).

## License

MIT
