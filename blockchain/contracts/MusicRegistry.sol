// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  MusicRegistry
 * @notice Smart contract unique centralisant l'enregistrement des droits musicaux,
 *         la certification des infractions et la simulation de distribution
 *         des redevances.
 *
 * @dev    Conçu dans le cadre du mémoire :
 *         "L'IA et la Blockchain au service de la lutte contre la piraterie musicale"
 *         Auteur : ADJINDA Adékin Olatobi Algis | Directeur : Pr. Eugène EZIN
 *
 *         Pipeline couvert :
 *           Étape 1 → registerWork()         : enregistrement de l'œuvre
 *           Étape 3 → certifyInfringement()  : certification de la preuve
 *           Étape 5 → simulateRoyaltyPayment(): simulation des redevances
 */
contract MusicRegistry {

    // ═══════════════════════════════════════════════════════════════════════
    // STRUCTURES
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @dev Représente une œuvre musicale enregistrée dans le système.
     *      Correspond à la classe AudioTrack du diagramme de classes.
     */
    struct Work {
        string   cid;            // CID IPFS de l'empreinte audio complète
        address[] recipients;   // Adresses Ethereum des ayants droit
        uint256[] shares;       // Parts en % de chaque ayant droit (somme = 100)
        uint256  registeredAt;  // Horodatage Unix d'enregistrement (block.timestamp)
        bool     exists;        // Sentinel : empêche l'écrasement silencieux
    }

    /**
     * @dev Représente une infraction certifiée on-chain.
     *      Correspond à la classe Proof du diagramme de classes.
     */
    struct Infringement {
        string  evidenceCID;   // CID IPFS du dossier de preuve (fichier suspect + rapport)
        bytes32 workHash;      // Hash de l'œuvre originale concernée
        uint256 certifiedAt;   // Horodatage de certification
    }


    // ═══════════════════════════════════════════════════════════════════════
    // STATE VARIABLES
    // ═══════════════════════════════════════════════════════════════════════

    /// @dev Registre principal : hash empreinte → œuvre
    mapping(bytes32 => Work)        private works;

    /// @dev Registre des infractions : hash preuve → infraction
    mapping(bytes32 => Infringement) private infringements;

    /// @dev Propriétaire du contrat (compte déployeur)
    address public owner;


    // ═══════════════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @notice Émis lors de l'enregistrement d'une nouvelle œuvre.
     * @param workHash   Hash SHA-256 de l'empreinte audio (identifiant unique)
     * @param cid        CID IPFS de l'empreinte
     * @param recipients Liste des adresses des ayants droit
     * @param shares     Parts respectives en pourcentage
     * @param timestamp  Horodatage d'enregistrement
     */
    event WorkRegistered(
        bytes32 indexed workHash,
        string          cid,
        address[]       recipients,
        uint256[]       shares,
        uint256         timestamp
    );

    /**
     * @notice Émis lors de la certification d'une infraction.
     * @param evidenceHash Hash de la preuve (calculé on-chain)
     * @param workHash     Hash de l'œuvre originale
     * @param evidenceCID  CID IPFS du dossier de preuve
     * @param timestamp    Horodatage de certification
     */
    event InfringementCertified(
        bytes32 indexed evidenceHash,
        bytes32 indexed workHash,
        string          evidenceCID,
        uint256         timestamp
    );

    /**
     * @notice Émis pour chaque bénéficiaire lors d'une simulation de redevances.
     * @param workHash    Hash de l'œuvre concernée
     * @param beneficiary Adresse du bénéficiaire
     * @param amount      Montant calculé (totalAmount × share / 100)
     * @param timestamp   Horodatage de la simulation
     */
    event PaymentSimulated(
        bytes32 indexed workHash,
        address indexed beneficiary,
        uint256         amount,
        uint256         timestamp
    );


    // ═══════════════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════════════

    modifier onlyOwner() {
        require(msg.sender == owner, "MusicRegistry: caller is not the owner");
        _;
    }

    modifier workMustExist(bytes32 workHash) {
        require(works[workHash].exists, "MusicRegistry: work not registered");
        _;
    }

    modifier workMustNotExist(bytes32 workHash) {
        require(!works[workHash].exists, "MusicRegistry: work already registered");
        _;
    }


    // ═══════════════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════════════

    constructor() {
        owner = msg.sender;
    }


    // ═══════════════════════════════════════════════════════════════════════
    // WRITE FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @notice Enregistre une œuvre musicale sur la blockchain.
     *         Correspond à l'étape 1 du pipeline.
     *
     * @param workHash   Hash SHA-256 de l'empreinte GraFPrint (bytes32)
     * @param cid        CID IPFS de l'empreinte audio complète
     * @param recipients Adresses Ethereum des ayants droit
     * @param shares     Parts en % de chaque ayant droit — doit sommer à 100
     *
     * @dev  Validations :
     *         - L'œuvre ne doit pas déjà être enregistrée
     *         - Au moins un bénéficiaire
     *         - recipients.length == shares.length
     *         - Aucune adresse nulle
     *         - Somme des parts == 100
     */
    function registerWork(
        bytes32          workHash,
        string  calldata cid,
        address[] calldata recipients,
        uint256[] calldata shares
    )
        external
        workMustNotExist(workHash)
    {
        require(bytes(cid).length > 0,       "MusicRegistry: empty CID");
        require(recipients.length > 0,        "MusicRegistry: no recipients provided");
        require(
            recipients.length == shares.length,
            "MusicRegistry: recipients and shares length mismatch"
        );

        uint256 totalShares = 0;
        for (uint256 i = 0; i < shares.length; i++) {
            require(
                recipients[i] != address(0),
                "MusicRegistry: zero address not allowed"
            );
            require(shares[i] > 0, "MusicRegistry: share must be greater than 0");
            totalShares += shares[i];
        }
        require(totalShares == 100, "MusicRegistry: shares must sum to exactly 100");

        // Copie en storage (les arrays calldata ne peuvent pas être stockés directement)
        Work storage w = works[workHash];
        w.cid          = cid;
        w.registeredAt = block.timestamp;
        w.exists       = true;

        for (uint256 i = 0; i < recipients.length; i++) {
            w.recipients.push(recipients[i]);
            w.shares.push(shares[i]);
        }

        emit WorkRegistered(workHash, cid, recipients, shares, block.timestamp);
    }

    /**
     * @notice Certifie une infraction en ancrant la preuve sur la blockchain.
     *         Correspond à l'étape 3 du pipeline.
     *
     * @param evidenceCID CID IPFS du dossier de preuve (fichier suspect + rapport forensique)
     * @param workHash    Hash de l'œuvre originale dont une copie a été détectée
     *
     * @return evidenceHash Hash unique de la preuve certifiée (calculé on-chain)
     *
     * @dev  Le hash de preuve est calculé comme keccak256(evidenceCID + workHash + timestamp)
     *       ce qui garantit son unicité et son horodatage infalsifiable.
     */
    function certifyInfringement(
        string  calldata evidenceCID,
        bytes32          workHash
    )
        external
        workMustExist(workHash)
        returns (bytes32 evidenceHash)
    {
        require(bytes(evidenceCID).length > 0, "MusicRegistry: empty evidence CID");

        evidenceHash = keccak256(
            abi.encodePacked(evidenceCID, workHash, block.timestamp, msg.sender)
        );

        infringements[evidenceHash] = Infringement({
            evidenceCID: evidenceCID,
            workHash:    workHash,
            certifiedAt: block.timestamp
        });

        emit InfringementCertified(evidenceHash, workHash, evidenceCID, block.timestamp);

        return evidenceHash;
    }

    /**
     * @notice Simule la distribution des redevances entre les ayants droit.
     *         Correspond à l'étape 5 du pipeline.
     *         Aucun transfert réel n'est effectué — seuls des événements sont émis.
     *
     * @param workHash    Hash de l'œuvre pour laquelle simuler la distribution
     * @param totalAmount Montant fictif total à distribuer (en unité arbitraire)
     *
     * @dev  Pour chaque bénéficiaire i :
     *         montant_i = (totalAmount × shares[i]) / 100
     *       Un événement PaymentSimulated est émis pour chaque bénéficiaire.
     */
    function simulateRoyaltyPayment(
        bytes32 workHash,
        uint256 totalAmount
    )
        external
        workMustExist(workHash)
    {
        require(totalAmount > 0, "MusicRegistry: totalAmount must be greater than 0");

        Work storage w = works[workHash];

        for (uint256 i = 0; i < w.recipients.length; i++) {
            uint256 amount = (totalAmount * w.shares[i]) / 100;
            emit PaymentSimulated(workHash, w.recipients[i], amount, block.timestamp);
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // READ FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @notice Vérifie si une œuvre est enregistrée dans le registre.
     * @param workHash Hash de l'empreinte à vérifier
     * @return bool true si l'œuvre est enregistrée
     */
    function isWorkRegistered(bytes32 workHash)
        external view returns (bool)
    {
        return works[workHash].exists;
    }

    /**
     * @notice Récupère les informations d'une œuvre enregistrée.
     * @param workHash Hash de l'empreinte à récupérer
     * @return cid          CID IPFS de l'empreinte
     * @return recipients   Adresses des ayants droit
     * @return shares       Parts respectives
     * @return registeredAt Horodatage d'enregistrement
     */
    function getWork(bytes32 workHash)
        external view
        workMustExist(workHash)
        returns (
            string   memory cid,
            address[] memory recipients,
            uint256[] memory shares,
            uint256          registeredAt
        )
    {
        Work storage w = works[workHash];
        return (w.cid, w.recipients, w.shares, w.registeredAt);
    }

    /**
     * @notice Récupère les informations d'une infraction certifiée.
     * @param evidenceHash Hash de la preuve (retourné par certifyInfringement)
     * @return evidenceCID CID IPFS du dossier de preuve
     * @return workHash    Hash de l'œuvre concernée
     * @return certifiedAt Horodatage de certification
     */
    function getInfringement(bytes32 evidenceHash)
        external view
        returns (
            string  memory evidenceCID,
            bytes32        workHash,
            uint256        certifiedAt
        )
    {
        Infringement storage inf = infringements[evidenceHash];
        require(inf.certifiedAt > 0, "MusicRegistry: infringement not found");
        return (inf.evidenceCID, inf.workHash, inf.certifiedAt);
    }
}