"""
Tests unitaires — BlockchainManager (avec mock Web3)
Couverture : connect_web3, register_work, store_proof,
             simulate_royalty_payment, verify_registration
"""
import json
import pytest
from pathlib     import Path
from unittest.mock import MagicMock, patch, PropertyMock

from web3 import Web3

from backend.core.blockchain_manager import BlockchainManager
from tests.conftest import make_work_hash

pytestmark = pytest.mark.unit


@pytest.fixture
def deployment_json(tmp_path) -> Path:
    """Génère un fichier deployment.json factice."""
    data = {
        "network": "ganache",
        "address": "0x" + "A" * 40,
        "deployer": "0x" + "B" * 40,
        "deployedAt": "2025-01-01T00:00:00",
        "abi": [
            {
                "name": "registerWork",
                "type": "function",
                "inputs": [
                    {"name": "workHash",   "type": "bytes32"},
                    {"name": "cid",        "type": "string"},
                    {"name": "recipients", "type": "address[]"},
                    {"name": "shares",     "type": "uint256[]"},
                ],
                "outputs": [],
                "stateMutability": "nonpayable"
            },
            {
                "name": "isWorkRegistered",
                "type": "function",
                "inputs": [{"name": "workHash", "type": "bytes32"}],
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view"
            },
            {
                "name": "certifyInfringement",
                "type": "function",
                "inputs": [
                    {"name": "evidenceCID", "type": "string"},
                    {"name": "workHash",    "type": "bytes32"},
                ],
                "outputs": [{"name": "evidenceHash", "type": "bytes32"}],
                "stateMutability": "nonpayable"
            },
            {
                "name": "simulateRoyaltyPayment",
                "type": "function",
                "inputs": [
                    {"name": "workHash",    "type": "bytes32"},
                    {"name": "totalAmount", "type": "uint256"},
                ],
                "outputs": [],
                "stateMutability": "nonpayable"
            },
            {
                "name": "WorkRegistered",
                "type": "event",
                "inputs": [
                    {"name": "workHash",   "type": "bytes32", "indexed": True},
                    {"name": "cid",        "type": "string"},
                    {"name": "recipients", "type": "address[]"},
                    {"name": "shares",     "type": "uint256[]"},
                    {"name": "timestamp",  "type": "uint256"},
                ]
            },
            {
                "name": "InfringementCertified",
                "type": "event",
                "inputs": [
                    {"name": "evidenceHash", "type": "bytes32", "indexed": True},
                    {"name": "workHash",     "type": "bytes32", "indexed": True},
                    {"name": "evidenceCID",  "type": "string"},
                    {"name": "timestamp",    "type": "uint256"},
                ]
            },
            {
                "name": "PaymentSimulated",
                "type": "event",
                "inputs": [
                    {"name": "workHash",    "type": "bytes32", "indexed": True},
                    {"name": "beneficiary", "type": "address", "indexed": True},
                    {"name": "amount",      "type": "uint256"},
                    {"name": "timestamp",   "type": "uint256"},
                ]
            }
        ]
    }
    path = tmp_path / "deployment.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def manager_with_mock_web3(deployment_json, monkeypatch):
    """
    BlockchainManager avec Web3 entièrement mocké.
    """
    monkeypatch.setattr(
        "backend.core.blockchain_manager.settings",
        MagicMock(
            ganache_url          = "http://127.0.0.1:7545",
            deployer_private_key = "0x" + "a" * 64,
            deployment_json      = deployment_json
        )
    )

    # Mock Web3
    mock_w3       = MagicMock()
    mock_w3.is_connected.return_value     = True
    mock_w3.eth.block_number              = 42
    mock_w3.eth.accounts                  = ["0x" + "C" * 40]
    mock_w3.eth.get_transaction_count.return_value = 1
    mock_w3.to_wei.return_value           = 20_000_000_000

    # Mock transaction
    mock_tx_hash    = b"\xab" * 32
    mock_receipt    = {
        "status":          1,
        "transactionHash": mock_tx_hash,
        "gasUsed":         150_000,
        "logs":            []
    }
    mock_w3.eth.send_raw_transaction.return_value           = mock_tx_hash
    mock_w3.eth.wait_for_transaction_receipt.return_value   = mock_receipt
    mock_w3.eth.get_transaction_receipt.return_value        = mock_receipt

    # Mock contrat
    mock_contract = MagicMock()
    mock_contract.functions.isWorkRegistered.return_value.call.return_value = False
    mock_contract.functions.getWork.return_value.call.return_value = (
        "QmTest", ["0x" + "E" * 40], [100], 1700000000
    )
    mock_contract.events.InfringementCertified.return_value\
        .process_receipt.return_value = [
            {"args": {"evidenceHash": b"\xcc" * 32}}
        ]
    mock_contract.events.PaymentSimulated.return_value\
        .process_receipt.return_value = [
            {"args": {"beneficiary": "0x" + "E" * 40,
                      "amount": 700, "timestamp": 1700000000}},
            {"args": {"beneficiary": "0x" + "F" * 40,
                      "amount": 300, "timestamp": 1700000000}},
        ]

    mock_w3.eth.contract.return_value = mock_contract
    mock_w3.to_checksum_address.side_effect = lambda x: x

    # Mock Account
    mock_account      = MagicMock()
    mock_account.address = "0x" + "D" * 40
    mock_account.key     = b"\xaa" * 32

    mock_signed    = MagicMock()
    mock_signed.raw_transaction = b"\x01" * 200

    with patch("backend.core.blockchain_manager.Web3") as MockWeb3, \
          patch("backend.core.blockchain_manager.Account") as MockAccount:

        MockWeb3.return_value               = mock_w3
        MockWeb3.to_hex.return_value = "0x" + "ab" * 32   # 66 caractères
        MockWeb3.HTTPProvider               = MagicMock()
        MockWeb3.to_checksum_address.side_effect = lambda x: x
        MockAccount.from_key.return_value   = mock_account
        mock_w3.eth.account.sign_transaction.return_value = mock_signed

        manager = BlockchainManager()
        manager.connect_web3()

        # Injection directe pour les tests
        manager._web3     = mock_w3
        manager._contract = mock_contract
        manager._account  = mock_account

        yield manager, mock_w3, mock_contract


class TestConnection:

    def test_is_connected_true(self, manager_with_mock_web3):
        manager, mock_w3, _ = manager_with_mock_web3
        mock_w3.is_connected.return_value = True
        assert manager.is_connected() is True

    def test_is_connected_false_when_web3_none(self):
        m = BlockchainManager()
        assert m.is_connected() is False

    def test_missing_deployment_json_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "backend.core.blockchain_manager.settings",
            MagicMock(
                ganache_url          = "http://127.0.0.1:7545",
                deployer_private_key = "",
                deployment_json      = tmp_path / "nonexistent.json"
            )
        )
        m = BlockchainManager()
        with pytest.raises(FileNotFoundError, match="deployment.json"):
            m._load_contract()


class TestRegisterWork:

    def test_register_returns_tx_hash(self, manager_with_mock_web3):
        manager, mock_w3, _ = manager_with_mock_web3
        mock_w3.eth.send_raw_transaction.return_value = bytes.fromhex("ab" * 32)

        tx = manager.register_work(
            "a" * 64, "QmTest",
            ["0x" + "E" * 40], [100]
        )
        assert tx.startswith("0x")
        assert len(tx) == 66

    def test_register_calls_contract_function(self, manager_with_mock_web3):
        manager, _, mock_contract = manager_with_mock_web3
        manager.register_work("a" * 64, "QmTest", ["0x" + "E" * 40], [100])
        mock_contract.functions.registerWork.assert_called_once()

    def test_failed_transaction_raises(self, manager_with_mock_web3):
        manager, mock_w3, _ = manager_with_mock_web3
        mock_w3.eth.wait_for_transaction_receipt.return_value = {
            "status": 0,
            "transactionHash": bytes.fromhex("ab" * 32),
            "gasUsed": 50_000, "logs": []
        }
        with pytest.raises(RuntimeError, match="Transaction échouée"):
            manager.register_work("a" * 64, "QmTest", ["0x" + "E" * 40], [100])


class TestVerifyRegistration:

    def test_verify_false_by_default(self, manager_with_mock_web3):
        manager, _, mock_contract = manager_with_mock_web3
        mock_contract.functions.isWorkRegistered.return_value.call.return_value = False
        assert manager.verify_registration("a" * 64) is False

    def test_verify_true_after_register(self, manager_with_mock_web3):
        manager, _, mock_contract = manager_with_mock_web3
        mock_contract.functions.isWorkRegistered.return_value.call.return_value = True
        assert manager.verify_registration("a" * 64) is True


class TestStoreProof:

    def test_store_proof_returns_tuple(self, manager_with_mock_web3):
        manager, _, _ = manager_with_mock_web3
        tx_hash, evidence_hash = manager.store_proof("QmEvidence", "a" * 64)
        assert tx_hash.startswith("0x")
        assert isinstance(evidence_hash, str)

    def test_evidence_hash_is_hex(self, manager_with_mock_web3):
        manager, _, _ = manager_with_mock_web3
        _, evidence_hash = manager.store_proof("QmEvidence", "a" * 64)
        assert all(c in "0123456789abcdef" for c in evidence_hash.lower())


class TestSimulateRoyaltyPayment:

    def test_returns_payments_list(self, manager_with_mock_web3):
        manager, _, _ = manager_with_mock_web3
        tx, payments = manager.simulate_royalty_payment("a" * 64, 1000)
        assert tx.startswith("0x")
        assert isinstance(payments, list)
        assert len(payments) == 2

    def test_payments_have_correct_structure(self, manager_with_mock_web3):
        manager, _, _ = manager_with_mock_web3
        _, payments = manager.simulate_royalty_payment("a" * 64, 1000)
        for p in payments:
            assert "beneficiary" in p
            assert "amount"      in p
            assert "timestamp"   in p

    def test_payment_amounts_sum_to_total(self, manager_with_mock_web3):
        manager, _, _ = manager_with_mock_web3
        _, payments = manager.simulate_royalty_payment("a" * 64, 1000)
        total = sum(p["amount"] for p in payments)
        assert total == 1000