require("dotenv").config({ path: ".env.local" });
require("dotenv").config(); // fallback to .env if .env.local doesn't exist

const url = process.env.DATABASE_URL;
const isProd = process.env.NODE_ENV === "production" || (url && url.includes("sslmode="));
const dialectOptions =
  isProd && url && !url.includes("localhost") && !url.includes("127.0.0.1")
    ? {
        ssl: {
          require: true,
          rejectUnauthorized: false,
        },
      }
    : {};

module.exports = {
  development: { url, dialect: "postgres", dialectOptions },
  production: { url, dialect: "postgres", dialectOptions },
};
