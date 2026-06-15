require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../.env" });

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },

  networks: {
    ganache: {
      url:      process.env.GANACHE_URL || "http://127.0.0.1:7545",
      chainId:  1337,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
                ? [process.env.DEPLOYER_PRIVATE_KEY]
                : { mnemonic: "test test test test test test test test test test test junk" }
    },

    hardhat: {
      chainId: 31337
    },

    // ⬇️ AJOUTER CECI ⬇️
    amoy: {
      url:      "https://rpc-amoy.polygon.technology",
      chainId:  80002,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
                ? [process.env.DEPLOYER_PRIVATE_KEY]
                : []
    },

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