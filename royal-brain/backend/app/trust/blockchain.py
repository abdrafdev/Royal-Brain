"""Blockchain Anchoring Service — Day 9.

Anchors entity hashes to an EVM-compatible network via real transactions.

Strategy:
- Single: send a 0-value transaction with tx.data = bytes32(entity_hash.hash_value)
- Batch: compute a Merkle root, then send a 0-value transaction with tx.data = bytes32(merkle_root)

Required environment configuration:
- EVM_RPC_URL
- EVM_CHAIN_ID
- EVM_PRIVATE_KEY

Optional:
- EVM_EXPLORER_TX_URL_BASE (e.g. https://sepolia.etherscan.io/tx)

No simulated anchoring is performed.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.trust.models import BlockchainAnchor, EntityHash


KNOWN_EXPLORER_TX_BASE: dict[str, str] = {
    # Backwards-compatible defaults; override with EVM_EXPLORER_TX_URL_BASE for your deployment.
    "polygon-mumbai": "https://mumbai.polygonscan.com/tx",
    "polygon-amoy": "https://amoy.polygonscan.com/tx",
    "sepolia": "https://sepolia.etherscan.io/tx",
}


def _compute_merkle_root(hashes: list[str]) -> str:
    """Compute Merkle root from list of SHA256 hex digests."""
    if not hashes:
        raise ValueError("Cannot compute Merkle root of empty list")

    if len(hashes) == 1:
        return hashes[0]

    next_level: list[str] = []
    for i in range(0, len(hashes), 2):
        if i + 1 < len(hashes):
            combined = hashes[i] + hashes[i + 1]
        else:
            combined = hashes[i] + hashes[i]  # Duplicate last hash if odd
        next_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())

    return _compute_merkle_root(next_level)


def _normalize_hex32(value: str) -> str:
    """Normalize a bytes32 hex string to 64 lowercase hex chars (no 0x)."""
    v = (value or "").strip().lower()
    if v.startswith("0x"):
        v = v[2:]
    if len(v) != 64:
        raise ValueError("Expected 32-byte hex string (64 hex chars).")
    allowed = set("0123456789abcdef")
    if any(c not in allowed for c in v):
        raise ValueError("Invalid hex string.")
    return v


def _build_explorer_url(*, blockchain_network: str, tx_hash: str) -> str | None:
    base = get_settings().evm_explorer_tx_url_base
    if base:
        return f"{base.rstrip('/')}/{tx_hash}"

    default_base = KNOWN_EXPLORER_TX_BASE.get((blockchain_network or "").strip().lower())
    if not default_base:
        return None
    return f"{default_base.rstrip('/')}/{tx_hash}"


def _send_anchor_tx(*, data_hex32: str, blockchain_network: str) -> tuple[str, int | None, datetime | None, str | None]:
    """Submit a real EVM transaction containing data_hex32.

    Returns:
        (tx_hash, block_number, block_timestamp, explorer_url)
    """
    settings = get_settings()
    if not settings.evm_rpc_url or not settings.evm_chain_id or not settings.evm_private_key:
        raise ValueError(
            "Blockchain anchoring is not configured. Set EVM_RPC_URL, EVM_CHAIN_ID, and EVM_PRIVATE_KEY."
        )

    from eth_account import Account
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(settings.evm_rpc_url))
    if not w3.is_connected():
        raise ValueError("Could not connect to EVM RPC URL.")

    data_hex32 = _normalize_hex32(data_hex32)

    acct = Account.from_key(settings.evm_private_key)
    from_addr = acct.address

    # Anchor by sending a 0-value tx to self with data = bytes32(value)
    tx: dict = {
        "from": from_addr,
        "to": from_addr,
        "value": 0,
        "nonce": w3.eth.get_transaction_count(from_addr),
        "chainId": int(settings.evm_chain_id),
        "data": "0x" + data_hex32,
    }

    # Prefer EIP-1559 fees when available.
    try:
        latest = w3.eth.get_block("latest")
        base_fee = latest.get("baseFeePerGas") if isinstance(latest, dict) else getattr(latest, "baseFeePerGas", None)
        if base_fee is not None:
            max_priority_fee = w3.to_wei(1, "gwei")
            tx["type"] = 2
            tx["maxPriorityFeePerGas"] = max_priority_fee
            tx["maxFeePerGas"] = int(base_fee) * 2 + int(max_priority_fee)
        else:
            tx["gasPrice"] = w3.eth.gas_price
    except Exception:
        tx["gasPrice"] = w3.eth.gas_price

    # Estimate gas.
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
    except Exception:
        tx["gas"] = 100000

    signed = acct.sign_transaction(tx)
    raw_tx = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
    tx_hash_bytes = w3.eth.send_raw_transaction(raw_tx)
    tx_hash = tx_hash_bytes.hex()  # 0x...

    block_number: int | None = None
    block_timestamp: datetime | None = None

    # Best-effort: wait briefly for a receipt to enrich metadata.
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        block_number = int(receipt.blockNumber)
        block = w3.eth.get_block(block_number)
        ts = block.get("timestamp") if isinstance(block, dict) else getattr(block, "timestamp", None)
        if ts is not None:
            block_timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except Exception:
        pass

    explorer_url = _build_explorer_url(blockchain_network=blockchain_network, tx_hash=tx_hash)
    return tx_hash, block_number, block_timestamp, explorer_url


def anchor_single_hash(
    db: Session,
    *,
    hash_id: int,
    user_id: int,
    blockchain_network: str = "polygon-mumbai",
) -> BlockchainAnchor:
    """Anchor a single entity hash to an EVM network."""
    entity_hash = db.get(EntityHash, hash_id)
    if not entity_hash:
        raise ValueError(f"EntityHash {hash_id} not found")

    tx_hash, block_number, block_timestamp, explorer_url = _send_anchor_tx(
        data_hex32=entity_hash.hash_value,
        blockchain_network=blockchain_network,
    )

    anchor = BlockchainAnchor(
        hash_id=hash_id,
        merkle_root=None,
        batch_id=None,
        blockchain_network=blockchain_network,
        transaction_hash=tx_hash,
        block_number=block_number,
        block_timestamp=block_timestamp,
        anchor_type="single",
        anchored_by_user_id=user_id,
        explorer_url=explorer_url,
    )

    db.add(anchor)
    db.commit()
    db.refresh(anchor)

    return anchor


def anchor_batch_hashes(
    db: Session,
    *,
    hash_ids: list[int],
    user_id: int,
    blockchain_network: str = "polygon-mumbai",
) -> list[BlockchainAnchor]:
    """Anchor multiple entity hashes using a Merkle tree root."""
    if not hash_ids:
        raise ValueError("No hashes provided for batch anchoring")

    # Fetch and deterministically order hashes (stable Merkle root).
    entity_hashes: list[EntityHash] = []
    for hid in hash_ids:
        h = db.get(EntityHash, hid)
        if h is None:
            raise ValueError("One or more EntityHash IDs not found")
        entity_hashes.append(h)

    entity_hashes.sort(key=lambda h: h.id)
    hash_values = [h.hash_value for h in entity_hashes]
    merkle_root = _compute_merkle_root(hash_values)

    batch_id = str(uuid.uuid4())

    tx_hash, block_number, block_timestamp, explorer_url = _send_anchor_tx(
        data_hex32=merkle_root,
        blockchain_network=blockchain_network,
    )

    anchors: list[BlockchainAnchor] = []
    for h in entity_hashes:
        anchor = BlockchainAnchor(
            hash_id=h.id,
            merkle_root=merkle_root,
            batch_id=batch_id,
            blockchain_network=blockchain_network,
            transaction_hash=tx_hash,
            block_number=block_number,
            block_timestamp=block_timestamp,
            anchor_type="batch",
            anchored_by_user_id=user_id,
            explorer_url=explorer_url,
        )
        db.add(anchor)
        anchors.append(anchor)

    db.commit()
    for anchor in anchors:
        db.refresh(anchor)

    return anchors


def get_anchor_for_hash(db: Session, hash_id: int) -> BlockchainAnchor | None:
    """Get blockchain anchor for a hash."""
    return (
        db.query(BlockchainAnchor)
        .filter(BlockchainAnchor.hash_id == hash_id)
        .order_by(BlockchainAnchor.anchored_at.desc())
        .first()
    )


def _expected_data_hex32_for_anchor(db: Session, *, anchor: BlockchainAnchor) -> str:
    if anchor.anchor_type == "batch":
        if not anchor.merkle_root:
            raise ValueError("Batch anchor missing merkle_root")
        return _normalize_hex32(anchor.merkle_root)

    if anchor.hash_id is None:
        raise ValueError("Single anchor missing hash_id")
    entity_hash = db.get(EntityHash, anchor.hash_id)
    if entity_hash is None:
        raise ValueError("EntityHash not found for anchor")
    return _normalize_hex32(entity_hash.hash_value)


def verify_anchor(db: Session, anchor_id: int) -> dict:
    """Verify blockchain anchor by checking the on-chain transaction.

    This validates:
    - tx exists and has a successful receipt
    - tx input data matches the expected bytes32 payload
    """
    anchor = db.get(BlockchainAnchor, anchor_id)
    if not anchor:
        raise ValueError(f"BlockchainAnchor {anchor_id} not found")

    settings = get_settings()
    if not settings.evm_rpc_url:
        raise ValueError("Blockchain verification not configured. Set EVM_RPC_URL.")

    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(settings.evm_rpc_url))
    if not w3.is_connected():
        raise ValueError("Could not connect to EVM RPC URL.")

    tx_hash = (anchor.transaction_hash or "").strip()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    expected = _expected_data_hex32_for_anchor(db, anchor=anchor)

    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        receipt = None

    if receipt is None:
        return {
            "anchor_id": anchor.id,
            "transaction_hash": tx_hash,
            "blockchain_network": anchor.blockchain_network,
            "explorer_url": anchor.explorer_url,
            "verified": False,
            "confirmation_status": "PENDING",
            "note": "Transaction receipt not found yet (pending or not propagated).",
        }

    # Update stored block metadata if missing.
    try:
        if anchor.block_number is None and getattr(receipt, "blockNumber", None) is not None:
            anchor.block_number = int(receipt.blockNumber)
            block = w3.eth.get_block(anchor.block_number)
            ts = block.get("timestamp") if isinstance(block, dict) else getattr(block, "timestamp", None)
            if ts is not None:
                anchor.block_timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            db.commit()
    except Exception:
        pass

    status_ok = int(getattr(receipt, "status", 0) or 0) == 1

    try:
        tx = w3.eth.get_transaction(tx_hash)
        tx_input = tx.get("input") if isinstance(tx, dict) else getattr(tx, "input", "")
        tx_input_norm = _normalize_hex32(str(tx_input))
    except Exception:
        tx_input_norm = ""

    if not status_ok:
        return {
            "anchor_id": anchor.id,
            "transaction_hash": tx_hash,
            "blockchain_network": anchor.blockchain_network,
            "explorer_url": anchor.explorer_url,
            "verified": False,
            "confirmation_status": "FAILED",
            "note": "Transaction receipt indicates failure.",
        }

    if tx_input_norm != expected:
        return {
            "anchor_id": anchor.id,
            "transaction_hash": tx_hash,
            "blockchain_network": anchor.blockchain_network,
            "explorer_url": anchor.explorer_url,
            "verified": False,
            "confirmation_status": "MISMATCH",
            "note": "Transaction input does not match expected anchored value.",
        }

    return {
        "anchor_id": anchor.id,
        "transaction_hash": tx_hash,
        "blockchain_network": anchor.blockchain_network,
        "explorer_url": anchor.explorer_url,
        "verified": True,
        "confirmation_status": "CONFIRMED",
        "note": None,
    }
