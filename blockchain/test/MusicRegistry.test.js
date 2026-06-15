const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

// ─── Données de test ──────────────────────────────────────────────────────────
const SAMPLE_WORK_HASH = ethers.encodeBytes32String("grafp_hash_oeuvre_1");
const SAMPLE_CID = "QmXyz123456789abcdefghijklmnopqrstuvwxyz";
const EVIDENCE_CID = "QmEvidence987654321zyxwvutsrqponmlkjih";
const TOTAL_AMOUNT = ethers.parseUnits("1000", 0); // 1000 unités fictives

// ─── Fixture ─────────────────────────────────────────────────────────────────
async function deployMusicRegistryFixture() {
  const [owner, artist, producer, label, moderator] = await ethers.getSigners();

  const MusicRegistry = await ethers.getContractFactory("MusicRegistry");
  const contract = await MusicRegistry.deploy();

  return { contract, owner, artist, producer, label, moderator };
}

// ═════════════════════════════════════════════════════════════════════════════
describe("MusicRegistry", function () {

  // ── Déploiement ─────────────────────────────────────────────────────────
  describe("Déploiement", function () {
    it("Doit définir le bon propriétaire", async function () {
      const { contract, owner } = await loadFixture(deployMusicRegistryFixture);

      expect(await contract.owner()).to.equal(owner.address);
    });
  });

  // ── registerWork ────────────────────────────────────────────────────────
  describe("registerWork()", function () {

    it("Doit enregistrer une œuvre avec succès et émettre WorkRegistered", async function () {
      const { contract, artist, producer } = await loadFixture(deployMusicRegistryFixture);

      const recipients = [artist.address, producer.address];
      const shares = [70, 30];

      await expect(
        contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, recipients, shares)
      )
        .to.emit(contract, "WorkRegistered")
        .withArgs(SAMPLE_WORK_HASH, SAMPLE_CID, recipients, shares, (ts) => ts > 0);

      expect(await contract.isWorkRegistered(SAMPLE_WORK_HASH)).to.equal(true);
    });

    it("Doit correctement stocker les informations de l'œuvre", async function () {
      const { contract, artist, producer } = await loadFixture(deployMusicRegistryFixture);

      const recipients = [artist.address, producer.address];
      const shares = [70, 30];

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, recipients, shares);

      const [cid, storedRecipients, storedShares, registeredAt] =
        await contract.getWork(SAMPLE_WORK_HASH);

      expect(cid).to.equal(SAMPLE_CID);
      expect(storedRecipients).to.deep.equal(recipients);
      expect(storedShares.map(s => Number(s))).to.deep.equal(shares);
      expect(registeredAt).to.be.gt(0);
    });

    it("Doit rejeter l'enregistrement d'une œuvre déjà présente", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100]);

      await expect(
        contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100])
      ).to.be.revertedWith("MusicRegistry: work already registered");
    });

    it("Doit rejeter si les parts ne somment pas à 100", async function () {
      const { contract, artist, producer } = await loadFixture(deployMusicRegistryFixture);

      await expect(
        contract.registerWork(
          SAMPLE_WORK_HASH, SAMPLE_CID,
          [artist.address, producer.address],
          [60, 30]  // somme = 90 ≠ 100
        )
      ).to.be.revertedWith("MusicRegistry: shares must sum to exactly 100");
    });

    it("Doit rejeter si recipients et shares ont des longueurs différentes", async function () {
      const { contract, artist, producer } = await loadFixture(deployMusicRegistryFixture);

      await expect(
        contract.registerWork(
          SAMPLE_WORK_HASH, SAMPLE_CID,
          [artist.address, producer.address],
          [100]  // 2 recipients, 1 share
        )
      ).to.be.revertedWith("MusicRegistry: recipients and shares length mismatch");
    });

    it("Doit rejeter une adresse nulle dans recipients", async function () {
      const { contract } = await loadFixture(deployMusicRegistryFixture);

      await expect(
        contract.registerWork(
          SAMPLE_WORK_HASH, SAMPLE_CID,
          [ethers.ZeroAddress],
          [100]
        )
      ).to.be.revertedWith("MusicRegistry: zero address not allowed");
    });

    it("Doit rejeter un CID vide", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);

      await expect(
        contract.registerWork(SAMPLE_WORK_HASH, "", [artist.address], [100])
      ).to.be.revertedWith("MusicRegistry: empty CID");
    });
  });

  // ── certifyInfringement ─────────────────────────────────────────────────
  describe("certifyInfringement()", function () {

    it("Doit certifier une infraction et émettre InfringementCertified", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100]);

      const tx = await contract.certifyInfringement(EVIDENCE_CID, SAMPLE_WORK_HASH);

      await expect(tx)
        .to.emit(contract, "InfringementCertified")
        .withArgs(
          (h) => h.length === 66,  // bytes32 en hex = 66 chars
          SAMPLE_WORK_HASH,
          EVIDENCE_CID,
          (ts) => ts > 0
        );
    });

    it("Doit retourner un hash de preuve non nul", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100]);

      const receipt = await (
        await contract.certifyInfringement(EVIDENCE_CID, SAMPLE_WORK_HASH)
      ).wait();

      const event = receipt.logs.find(
        log => log.fragment?.name === "InfringementCertified"
      );
      expect(event).to.not.be.undefined;
      expect(event.args.evidenceHash).to.not.equal(ethers.ZeroHash);
    });

    it("Doit rejeter la certification sur une œuvre non enregistrée", async function () {
      const { contract } = await loadFixture(deployMusicRegistryFixture);

      const unknownHash = ethers.encodeBytes32String("unknown_hash");

      await expect(
        contract.certifyInfringement(EVIDENCE_CID, unknownHash)
      ).to.be.revertedWith("MusicRegistry: work not registered");
    });
  });

  // ── simulateRoyaltyPayment ───────────────────────────────────────────────
  describe("simulateRoyaltyPayment()", function () {

    it("Doit émettre un PaymentSimulated par bénéficiaire avec le bon montant", async function () {
      const { contract, artist, producer, label } =
        await loadFixture(deployMusicRegistryFixture);

      const recipients = [artist.address, producer.address, label.address];
      const shares = [60, 30, 10];

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, recipients, shares);

      const tx = await contract.simulateRoyaltyPayment(SAMPLE_WORK_HASH, TOTAL_AMOUNT);

      // Artiste : 60% de 1000 = 600
      await expect(tx)
        .to.emit(contract, "PaymentSimulated")
        .withArgs(SAMPLE_WORK_HASH, artist.address, 600n, (ts) => ts > 0);

      // Producteur : 30% de 1000 = 300
      await expect(tx)
        .to.emit(contract, "PaymentSimulated")
        .withArgs(SAMPLE_WORK_HASH, producer.address, 300n, (ts) => ts > 0);

      // Label : 10% de 1000 = 100
      await expect(tx)
        .to.emit(contract, "PaymentSimulated")
        .withArgs(SAMPLE_WORK_HASH, label.address, 100n, (ts) => ts > 0);
    });

    it("Doit émettre exactement N événements pour N bénéficiaires", async function () {
      const { contract, artist, producer } =
        await loadFixture(deployMusicRegistryFixture);

      await contract.registerWork(
        SAMPLE_WORK_HASH, SAMPLE_CID,
        [artist.address, producer.address],
        [70, 30]
      );

      const receipt = await (
        await contract.simulateRoyaltyPayment(SAMPLE_WORK_HASH, TOTAL_AMOUNT)
      ).wait();

      const events = receipt.logs.filter(
        log => log.fragment?.name === "PaymentSimulated"
      );
      expect(events.length).to.equal(2);
    });

    it("Doit rejeter un montant nul", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);

      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100]);

      await expect(
        contract.simulateRoyaltyPayment(SAMPLE_WORK_HASH, 0)
      ).to.be.revertedWith("MusicRegistry: totalAmount must be greater than 0");
    });

    it("Doit rejeter sur une œuvre non enregistrée", async function () {
      const { contract } = await loadFixture(deployMusicRegistryFixture);

      await expect(
        contract.simulateRoyaltyPayment(
          ethers.encodeBytes32String("inexistant"),
          TOTAL_AMOUNT
        )
      ).to.be.revertedWith("MusicRegistry: work not registered");
    });
  });

  // ── isWorkRegistered ─────────────────────────────────────────────────────
  describe("isWorkRegistered()", function () {

    it("Doit retourner false pour une œuvre non enregistrée", async function () {
      const { contract } = await loadFixture(deployMusicRegistryFixture);
      expect(await contract.isWorkRegistered(SAMPLE_WORK_HASH)).to.equal(false);
    });

    it("Doit retourner true après enregistrement", async function () {
      const { contract, artist } = await loadFixture(deployMusicRegistryFixture);
      await contract.registerWork(SAMPLE_WORK_HASH, SAMPLE_CID, [artist.address], [100]);
      expect(await contract.isWorkRegistered(SAMPLE_WORK_HASH)).to.equal(true);
    });
  });

});