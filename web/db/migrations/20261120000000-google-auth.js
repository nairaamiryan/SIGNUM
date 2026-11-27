"use strict";

module.exports = {
    async up(q, S) {
        await q.addColumn("users", "authProvider", {
            type: S.STRING,
            allowNull: false,
            defaultValue: "local",
        });
        await q.addColumn("users", "googleId", { type: S.STRING });
        await q.addColumn("users", "avatarUrl", { type: S.STRING(2048) });

        // Accounts created with Google have no password.
        await q.changeColumn("users", "passwordHash", { type: S.STRING, allowNull: true });

        // PostgreSQL treats NULLs as distinct, so many users may have no googleId.
        await q.addIndex("users", ["googleId"], { unique: true, name: "users_google_id_unique" });

        await q.addConstraint("users", {
            fields: ["authProvider"],
            type: "check",
            where: { authProvider: ["local", "google"] },
            name: "users_auth_provider_valid",
        });
        await q.sequelize.query(
            `ALTER TABLE "users" ADD CONSTRAINT "users_local_requires_password" ` +
                `CHECK ("authProvider" <> 'local' OR "passwordHash" IS NOT NULL)`,
        );
    },

    async down(q, S) {
        const [rows] = await q.sequelize.query(
            `SELECT COUNT(*)::int AS count FROM "users" WHERE "passwordHash" IS NULL`,
        );
        if (rows[0].count > 0) {
            throw new Error("Cannot revert: accounts without a password exist (Google sign-in).");
        }

        await q.sequelize.query(
            `ALTER TABLE "users" DROP CONSTRAINT "users_local_requires_password"`,
        );
        await q.removeConstraint("users", "users_auth_provider_valid");
        await q.removeIndex("users", "users_google_id_unique");
        await q.changeColumn("users", "passwordHash", { type: S.STRING, allowNull: false });
        await q.removeColumn("users", "avatarUrl");
        await q.removeColumn("users", "googleId");
        await q.removeColumn("users", "authProvider");
    },
};
