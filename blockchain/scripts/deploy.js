const { ethers } = require("hardhat");
const fs   = require("fs");
const path = require("path");

async function main() {
  console.log("╔══════════════════════════════════════════════════════╗");
  console.log("║    Déploiement MusicRegistry — Mémoire IA+Blockchain ║");
  console.log("╚══════════════════════════════════════════════════════╝\n");

  // ── Récupération du compte déployeur ──────────────────────────────────────
  const [deployer] = await ethers.getSigners();
  const balance    = await ethers.provider.getBalance(deployer.address);

  console.log(`Compte déployeur  : ${deployer.address}`);
  console.log(`Solde             : ${ethers.formatEther(balance)} ETH\n`);

  // ── Déploiement ───────────────────────────────────────────────────────────
  console.log("Déploiement du contrat MusicRegistry...");
  const MusicRegistry = await ethers.getContractFactory("MusicRegistry");
  const contract      = await MusicRegistry.deploy();

  await contract.waitForDeployment();
  const address = await contract.getAddress();

  console.log(`✅ MusicRegistry déployé à l'adresse : ${address}\n`);

  // ── Vérification post-déploiement ─────────────────────────────────────────
  const owner = await contract.owner();
  console.log(`Propriétaire du contrat : ${owner}`);
  console.log(`Correspondance deployer : ${owner === deployer.address ? "✅ OK" : "❌ ERREUR"}\n`);

  // ── Sauvegarde de l'adresse et de l'ABI pour Web3.py ─────────────────────
  const deploymentInfo = {
    network:     network.name,
    address:     address,
    deployer:    deployer.address,
    deployedAt:  new Date().toISOString(),
    abi:         JSON.parse(
                   fs.readFileSync(
                     path.join(__dirname, "../artifacts/contracts/MusicRegistry.sol/MusicRegistry.json"),
                     "utf8"
                   )
                 ).abi
  };

  // Sauvegarde dans blockchain/artifacts (lu par BlockchainManager)
  const outputPath = path.join(__dirname, "../artifacts/deployment.json");
  fs.writeFileSync(outputPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`📄 Infos de déploiement sauvegardées : ${outputPath}`);

  // Sauvegarde également dans backend pour que Web3.py puisse y accéder directement
  const backendPath = path.join(__dirname, "../../backend/db/deployment.json");
  if (fs.existsSync(path.dirname(backendPath))) {
    fs.writeFileSync(backendPath, JSON.stringify(deploymentInfo, null, 2));
    console.log(`📄 Copie backend sauvegardée          : ${backendPath}`);
  }

  console.log("\n╔══════════════════════════════════════════════════════╗");
  console.log("║               Déploiement terminé ✅                 ║");
  console.log("╚══════════════════════════════════════════════════════╝");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Erreur de déploiement :", error);
    process.exit(1);
  });