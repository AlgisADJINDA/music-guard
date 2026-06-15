"""
BlockchainManager — Couche blockchain.

Façade centralisant toutes les interactions avec le smart contract
MusicRegistry via Web3.py (JSON-RPC vers Ganache ou Polygon).

Correspond à la classe BlockchainManager du diagramme de classes.
"""
import json
import logging
from pathlib import Path
from typing  import Optional

from web3                    import Web3
from eth_account             import Account

from backend.config import settings

logger = logging.getLogger(__name__)


class BlockchainManager:
    """
    Interface Python vers le smart contract MusicRegistry déployé sur Ganache.

    Attributs privés
    ----------------
    _web3     : Instance Web3 connectée à Ganache
    _contract : Instance du contrat MusicRegistry
    _account  : Compte Ethereum utilisé pour signer les transactions
    """

    def __init__(self):
        self._web3:     Optional[Web3]  = None
        self._contract: Optional[object] = None
        self._account:  Optional[object] = None
        logger.info("BlockchainManager initialisé")

    # ── Connexion ─────────────────────────────────────────────────────────

    def connect_web3(self, provider_url: Optional[str] = None) -> None:
        """
        Établit la connexion Web3 et charge le contrat MusicRegistry.

        Lit le fichier deployment.json généré par le script deploy.js
        de l'étape 1 pour obtenir l'adresse et l'ABI du contrat.

        Parameters
        ----------
        provider_url : str, optional
            URL du nœud Ethereum. Par défaut : settings.ganache_url
        """
        url = provider_url or settings.ganache_url
        self._web3 = Web3(Web3.HTTPProvider(url))

        if not self._web3.is_connected():
            raise ConnectionError(
                f"Impossible de se connecter à la blockchain : {url}\n"
                f"Vérifier que Ganache est démarré sur ce port."
            )

        # Chargement du compte déployeur depuis la clé privée .env
        if settings.deployer_private_key:
            self._account = Account.from_key(settings.deployer_private_key)
            logger.info(f"Compte chargé : {self._account.address}")
        else:
            # Fallback : premier compte Ganache (développement uniquement)
            self._account = self._web3.eth.accounts[0]
            logger.warning(
                "DEPLOYER_PRIVATE_KEY non défini — "
                "utilisation du premier compte Ganache (dev seulement)"
            )

        # Chargement de l'ABI et de l'adresse du contrat
        self._load_contract()
        logger.info(
            f"Web3 connecté à {url} | "
            f"Block : {self._web3.eth.block_number}"
        )

    def _load_contract(self) -> None:
        """Charge le contrat MusicRegistry depuis deployment.json."""
        deployment_path = settings.deployment_json

        if not deployment_path.exists():
            raise FileNotFoundError(
                f"deployment.json introuvable : {deployment_path}\n"
                f"Lancer d'abord : cd blockchain && "
                f"npx hardhat run scripts/deploy.js --network ganache"
            )

        with open(deployment_path, "r") as f:
            deployment = json.load(f)

        address = Web3.to_checksum_address(deployment["address"])
        abi     = deployment["abi"]

        self._contract = self._web3.eth.contract(address=address, abi=abi)
        logger.info(f"Contrat MusicRegistry chargé : {address}")

    # ── Transactions ──────────────────────────────────────────────────────

    def _send_transaction(self, tx_function) -> str:
        """
        Signe et envoie une transaction, attend la confirmation.

        Parameters
        ----------
        tx_function : Fonction de contrat préparée (ex: contract.functions.xxx())

        Returns
        -------
        str : Hash de transaction (hex)
        """
        account_address = (
            self._account.address
            if hasattr(self._account, "address")
            else self._account
        )

        tx = tx_function.build_transaction({
            "from":     account_address,
            "nonce":    self._web3.eth.get_transaction_count(account_address),
            "gas":      500_000,
            "gasPrice": self._web3.to_wei("20", "gwei")
        })

        if hasattr(self._account, "key"):
            # Signature avec clé privée explicite
            signed  = self._web3.eth.account.sign_transaction(tx, self._account.key)
            tx_hash = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        else:
            # Mode développement Ganache (compte déverrouillé)
            tx_hash = self._web3.eth.send_transaction(tx)

        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] != 1:
            raise RuntimeError(f"Transaction échouée : {tx_hash.hex()}")

        return Web3.to_hex(tx_hash)

    # ── Interface publique ────────────────────────────────────────────────

    def register_work(
        self,
        work_hash:  str,
        cid:        str,
        recipients: list[str],
        shares:     list[int]
    ) -> str:
        """
        Enregistre une œuvre dans MusicRegistry.
        Correspond à l'étape 1 du pipeline.

        Parameters
        ----------
        work_hash  : str        Hash hex SHA-256 de l'empreinte GraFPrint
        cid        : str        CID IPFS de l'empreinte audio
        recipients : list[str]  Adresses Ethereum des ayants droit
        shares     : list[int]  Parts respectives (somme = 100)

        Returns
        -------
        str : Hash de transaction blockchain
        """
        work_hash_bytes = bytes.fromhex(work_hash)

        recipients_checksummed = [
            Web3.to_checksum_address(r) for r in recipients
        ]

        tx_hash = self._send_transaction(
            self._contract.functions.registerWork(
                work_hash_bytes,
                cid,
                recipients_checksummed,
                shares
            )
        )

        logger.info(f"Œuvre enregistrée on-chain | tx : {tx_hash[:16]}...")
        return tx_hash

    def store_proof(self, evidence_cid: str, work_hash: str) -> tuple[str, str]:
        """
        Certifie une infraction en ancrant la preuve sur la blockchain.
        Correspond à l'étape 3 du pipeline.

        Parameters
        ----------
        evidence_cid : str  CID IPFS du dossier de preuve
        work_hash    : str  Hash de l'œuvre originale concernée

        Returns
        -------
        tuple[str, str] : (tx_hash, evidence_hash)
            - tx_hash       : Hash de transaction blockchain
            - evidence_hash : Hash de preuve calculé on-chain (bytes32 hex)
        """
        work_hash_bytes = bytes.fromhex(work_hash)

        tx_hash = self._send_transaction(
            self._contract.functions.certifyInfringement(
                evidence_cid,
                work_hash_bytes
            )
        )

        # Récupération du evidence_hash depuis les logs de la transaction
        receipt = self._web3.eth.get_transaction_receipt(tx_hash)
        logs    = self._contract.events.InfringementCertified().process_receipt(receipt)
        evidence_hash = logs[0]["args"]["evidenceHash"].hex() if logs else ""

        logger.info(
            f"Infraction certifiée on-chain | "
            f"tx : {tx_hash[:16]}... | "
            f"evidence : {evidence_hash[:16]}..."
        )
        return tx_hash, evidence_hash

    def simulate_royalty_payment(
        self,
        work_hash:    str,
        total_amount: int
    ) -> tuple[str, list[dict]]:
        """
        Déclenche la simulation de distribution des redevances.
        Correspond à l'étape 5 du pipeline.

        Parameters
        ----------
        work_hash    : str  Hash de l'œuvre enregistrée
        total_amount : int  Montant fictif total à distribuer

        Returns
        -------
        tuple[str, list[dict]] : (tx_hash, payments)
            - tx_hash  : Hash de transaction blockchain
            - payments : Liste des paiements simulés par bénéficiaire
        """
        work_hash_bytes = bytes.fromhex(work_hash)

        tx_hash = self._send_transaction(
            self._contract.functions.simulateRoyaltyPayment(
                work_hash_bytes,
                total_amount
            )
        )

        # Récupération des événements PaymentSimulated émis
        receipt  = self._web3.eth.get_transaction_receipt(tx_hash)
        logs     = self._contract.events.PaymentSimulated().process_receipt(receipt)
        payments = [
            {
                "beneficiary": log["args"]["beneficiary"],
                "amount":      log["args"]["amount"],
                "timestamp":   log["args"]["timestamp"]
            }
            for log in logs
        ]

        logger.info(
            f"Redevances simulées | tx : {tx_hash[:16]}... | "
            f"{len(payments)} bénéficiaire(s)"
        )
        return tx_hash, payments

    def verify_registration(self, work_hash: str) -> bool:
        """
        Vérifie qu'une œuvre est enregistrée dans MusicRegistry.

        Parameters
        ----------
        work_hash : str  Hash hex de l'empreinte à vérifier

        Returns
        -------
        bool : True si l'œuvre est dans le registre on-chain
        """
        work_hash_bytes = bytes.fromhex(work_hash)
        return self._contract.functions.isWorkRegistered(work_hash_bytes).call()

    def get_work(self, work_hash: str) -> dict:
        """
        Récupère les informations d'une œuvre depuis la blockchain.

        Returns
        -------
        dict : {cid, recipients, shares, registered_at}
        """
        work_hash_bytes = bytes.fromhex(work_hash)
        cid, recipients, shares, registered_at = \
            self._contract.functions.getWork(work_hash_bytes).call()
        return {
            "cid":           cid,
            "recipients":    list(recipients),
            "shares":        [int(s) for s in shares],
            "registered_at": registered_at
        }

    def is_connected(self) -> bool:
        """Vérifie que la connexion Web3 est active."""
        return self._web3 is not None and self._web3.is_connected()