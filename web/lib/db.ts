import { Sequelize, DataTypes } from "sequelize";
import pg from "pg";
import { logger } from "@/lib/logger";

const globalForDb = globalThis as unknown as {
  sequelize?: Sequelize;
  dbAuthChecked?: boolean;
};

const dbUrl = process.env.DATABASE_URL as string;
const isProd = process.env.NODE_ENV === "production" || (dbUrl && dbUrl.includes("sslmode="));
const dialectOptions =
  isProd && dbUrl && !dbUrl.includes("localhost") && !dbUrl.includes("127.0.0.1")
    ? {
        ssl: {
          require: true,
          rejectUnauthorized: false,
        },
      }
    : undefined;

export const sequelize =
  globalForDb.sequelize ??
  new Sequelize(dbUrl, {
    dialect: "postgres",
    dialectModule: pg,
    dialectOptions,
    benchmark: true,
    logging: (sql: string, ms?: number) => {
      const slow = Number(process.env.DB_SLOW_QUERY_MS ?? 200);
      if (typeof ms === "number" && ms >= slow) {
        logger.warn("DB", `Slow query (${ms}ms): ${sql.slice(0, 300)}`);
      } else {
        logger.debug("DB", sql.slice(0, 300));
      }
    },
  });

if (process.env.NODE_ENV !== "production") globalForDb.sequelize = sequelize;

export async function checkDbConnection(): Promise<boolean> {
  try {
    await sequelize.authenticate();
    logger.info("DB", "Database connection verified successfully.");
    return true;
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    logger.error("DB", `Database connection failed: ${errorMsg}`);
    return false;
  }
}

if (!globalForDb.dbAuthChecked) {
  globalForDb.dbAuthChecked = true;
  checkDbConnection().catch(() => {});
}

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
