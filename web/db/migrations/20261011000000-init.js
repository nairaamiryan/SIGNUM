"use strict";

module.exports = {
  async up(q, S) {
    await q.createTable("users", {
      id: { type: S.UUID, primaryKey: true },
      email: { type: S.STRING, allowNull: false, unique: true },
      name: { type: S.STRING },
      passwordHash: { type: S.STRING, allowNull: false },
      createdAt: { type: S.DATE, allowNull: false },
      updatedAt: { type: S.DATE, allowNull: false },
    });

    await q.createTable("recognition_sessions", {
      id: { type: S.UUID, primaryKey: true },
      userId: {
        type: S.UUID,
        allowNull: false,
        references: { model: "users", key: "id" },
        onDelete: "CASCADE",
      },
      status: { type: S.STRING, allowNull: false, defaultValue: "ACTIVE" },
      startedAt: { type: S.DATE, allowNull: false },
      endedAt: { type: S.DATE },
      createdAt: { type: S.DATE, allowNull: false },
      updatedAt: { type: S.DATE, allowNull: false },
    });
    await q.addIndex("recognition_sessions", ["userId"]);

    await q.createTable("recognized_gestures", {
      id: { type: S.UUID, primaryKey: true },
      sessionId: {
        type: S.UUID,
        allowNull: false,
        references: { model: "recognition_sessions", key: "id" },
        onDelete: "CASCADE",
      },
      gloss: { type: S.STRING, allowNull: false },
      classId: { type: S.INTEGER },
      confidence: { type: S.FLOAT, allowNull: false },
      landmarkData: { type: S.JSONB },
      recognizedAt: { type: S.DATE, allowNull: false },
      createdAt: { type: S.DATE, allowNull: false },
      updatedAt: { type: S.DATE, allowNull: false },
    });
    await q.addIndex("recognized_gestures", ["sessionId"]);

    await q.createTable("captions", {
      id: { type: S.UUID, primaryKey: true },
      sessionId: {
        type: S.UUID,
        allowNull: false,
        references: { model: "recognition_sessions", key: "id" },
        onDelete: "CASCADE",
      },
      text: { type: S.TEXT, allowNull: false },
      glosses: { type: S.ARRAY(S.STRING), allowNull: false, defaultValue: [] },
      confidence: { type: S.FLOAT },
      createdAt: { type: S.DATE, allowNull: false },
      updatedAt: { type: S.DATE, allowNull: false },
    });
    await q.addIndex("captions", ["sessionId"]);
  },

  async down(q) {
    await q.dropTable("captions");
    await q.dropTable("recognized_gestures");
    await q.dropTable("recognition_sessions");
    await q.dropTable("users");
  },
};
