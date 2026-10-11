require("dotenv").config({ path: ".env.local" });

const url = process.env.DATABASE_URL;
module.exports = {
  development: { url, dialect: "postgres" },
  production: { url, dialect: "postgres" },
};
