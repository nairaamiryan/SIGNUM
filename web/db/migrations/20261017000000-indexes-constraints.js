"use strict";

module.exports = {
  async up(q) {
    await q.addIndex("captions", ["sessionId", "createdAt"], { name: "captions_session_created_idx" });
    await q.addIndex("recognized_gestures", ["sessionId", "recognizedAt"], { name: "gestures_session_recognized_idx" });
    await q.addIndex("recognition_sessions", ["userId", "startedAt"], { name: "sessions_user_started_idx" });

    await q.addConstraint("recognized_gestures", {
      fields: ["confidence"],
      type: "check",
      where: { confidence: { [q.sequelize.Sequelize.Op.between]: [0, 1] } },
      name: "gestures_confidence_range",
    });
    await q.addConstraint("captions", {
      fields: ["confidence"],
      type: "check",
      where: { confidence: { [q.sequelize.Sequelize.Op.or]: [{ [q.sequelize.Sequelize.Op.is]: null }, { [q.sequelize.Sequelize.Op.between]: [0, 1] }] } },
      name: "captions_confidence_range",
    });
    await q.addConstraint("recognition_sessions", {
      fields: ["status"],
      type: "check",
      where: { status: ["ACTIVE", "ENDED"] },
      name: "sessions_status_valid",
    });
  },

  async down(q) {
    await q.removeConstraint("recognition_sessions", "sessions_status_valid");
    await q.removeConstraint("captions", "captions_confidence_range");
    await q.removeConstraint("recognized_gestures", "gestures_confidence_range");
    await q.removeIndex("recognition_sessions", "sessions_user_started_idx");
    await q.removeIndex("recognized_gestures", "gestures_session_recognized_idx");
    await q.removeIndex("captions", "captions_session_created_idx");
  },
};
