require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../.env" });

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },

  networks: {
    // ── Ganache local (développement) ──────────────────────────────────────
    ganache: {
      url:      process.env.GANACHE_URL || "http://127.0.0.1:7545",
      chainId:  1337,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
                ? [process.env.DEPLOYER_PRIVATE_KEY]
                : { mnemonic: "test test test test test test test test test test test junk" }
    },

    // ── Hardhat Network (tests automatiques) ───────────────────────────────
    hardhat: {
      chainId: 31337
    },

    // ── Polygon Mumbai (production future) ─────────────────────────────────
    polygon_mumbai: {
      url:      process.env.POLYGON_RPC_URL || "",
      accounts: process.env.DEPLOYER_PRIVATE_KEY
                ? [process.env.DEPLOYER_PRIVATE_KEY]
                : []
    }
  },

  paths: {
    sources:   "./contracts",
    tests:     "./test",
    cache:     "./cache",
    artifacts: "./artifacts"
  }
};