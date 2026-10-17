import { Sequelize, DataTypes } from "sequelize";
import pg from "pg";

const globalForDb = globalThis as unknown as { sequelize?: Sequelize };

export const sequelize =
  globalForDb.sequelize ??
  new Sequelize(process.env.DATABASE_URL as string, {
    dialect: "postgres",
    dialectModule: pg,
    logging: false,
  });

if (process.env.NODE_ENV !== "production") globalForDb.sequelize = sequelize;

function init() {
  if (sequelize.models.User) return;

  const User = sequelize.define(
    "User",
    {
      id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
      email: { type: DataTypes.STRING, allowNull: false, unique: true },
      name: { type: DataTypes.STRING },
      passwordHash: { type: DataTypes.STRING, allowNull: false },
    },
    { tableName: "users" }
  );

  const RecognitionSession = sequelize.define(
    "RecognitionSession",
    {
      id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
      userId: { type: DataTypes.UUID, allowNull: false },
      status: {
        type: DataTypes.STRING,
        allowNull: false,
        defaultValue: "ACTIVE",
        validate: { isIn: [["ACTIVE", "ENDED"]] },
      },
      startedAt: { type: DataTypes.DATE, allowNull: false, defaultValue: DataTypes.NOW },
      endedAt: { type: DataTypes.DATE },
    },
    { tableName: "recognition_sessions" }
  );

  const RecognizedGesture = sequelize.define(
    "RecognizedGesture",
    {
      id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
      sessionId: { type: DataTypes.UUID, allowNull: false },
      gloss: { type: DataTypes.STRING, allowNull: false },
      classId: { type: DataTypes.INTEGER },
      confidence: { type: DataTypes.FLOAT, allowNull: false },
      landmarkData: { type: DataTypes.JSONB },
      recognizedAt: { type: DataTypes.DATE, allowNull: false, defaultValue: DataTypes.NOW },
    },
    { tableName: "recognized_gestures" }
  );

  const Caption = sequelize.define(
    "Caption",
    {
      id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
      sessionId: { type: DataTypes.UUID, allowNull: false },
      text: { type: DataTypes.TEXT, allowNull: false },
      glosses: { type: DataTypes.ARRAY(DataTypes.STRING), allowNull: false, defaultValue: [] },
      confidence: { type: DataTypes.FLOAT },
    },
    { tableName: "captions" }
  );

  User.hasMany(RecognitionSession, { foreignKey: "userId", onDelete: "CASCADE" });
  RecognitionSession.belongsTo(User, { foreignKey: "userId" });
  RecognitionSession.hasMany(RecognizedGesture, { foreignKey: "sessionId", onDelete: "CASCADE" });
  RecognizedGesture.belongsTo(RecognitionSession, { foreignKey: "sessionId" });
  RecognitionSession.hasMany(Caption, { foreignKey: "sessionId", onDelete: "CASCADE" });
  Caption.belongsTo(RecognitionSession, { foreignKey: "sessionId" });
}

init();

export const User = sequelize.models.User;
export const RecognitionSession = sequelize.models.RecognitionSession;
export const RecognizedGesture = sequelize.models.RecognizedGesture;
export const Caption = sequelize.models.Caption;
