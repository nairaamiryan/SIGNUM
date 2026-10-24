import fs from "fs";
import path from "path";
import { createRequire } from "module";
import winston from "winston";
import DailyRotateFile from "winston-daily-rotate-file";

type ArchiverFactory = (
  format: "zip",
  options?: { zlib?: { level: number } }
) => import("stream").Transform & {
  file(src: string, data: { name: string }): void;
  finalize(): Promise<void>;
};

export type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";
export type LogComponent = "APP" | "GESTURE_SERVICE" | "DB";

interface LogOptions {
  audit?: boolean;
  sessionId?: string | null;
}

const require = createRequire(import.meta.url);
const archiver = require("archiver") as unknown as ArchiverFactory;

const LOG_DIR = path.resolve(/*turbopackIgnore: true*/ process.env.LOG_DIR ?? "logs");
const MAX_SIZE_MB = process.env.LOG_MAX_SIZE_MB ?? "50";
const RETENTION_DAYS = Number(process.env.LOG_RETENTION_DAYS ?? 30);
const LEVEL = (process.env.LOG_LEVEL ?? "INFO").toLowerCase();

function zipFile(src: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(dest);
    const archive = archiver("zip", { zlib: { level: 9 } });
    output.on("close", () => resolve());
    archive.on("error", reject);
    archive.pipe(output);
    archive.file(src, { name: path.basename(src) });
    void archive.finalize();
  });
}

async function zipAndRemove(file: string) {
  if (!fs.existsSync(file)) return;
  await zipFile(file, `${file}.zip`);
  await fs.promises.unlink(file);
}

async function cleanupOldArchives() {
  const cutoff = Date.now() - RETENTION_DAYS * 24 * 60 * 60 * 1000;
  for (const name of await fs.promises.readdir(/*turbopackIgnore: true*/ LOG_DIR)) {
    if (!name.endsWith(".zip")) continue;
    const full = path.join(/*turbopackIgnore: true*/ LOG_DIR, name);
    const stat = await fs.promises.stat(/*turbopackIgnore: true*/ full);
    if (stat.mtimeMs < cutoff) await fs.promises.unlink(full);
  }
}

// After a server restart, zip logs left over from previous days.
async function zipStaleLogs() {
  const today = new Date().toISOString().slice(0, 10);
  for (const name of await fs.promises.readdir(/*turbopackIgnore: true*/ LOG_DIR)) {
    const m = name.match(/^signum-(\d{4}-\d{2}-\d{2})\.log(\.\d+)?$/);
    if (m && m[1] < today) await zipAndRemove(path.join(/*turbopackIgnore: true*/ LOG_DIR, name));
  }
  await cleanupOldArchives();
}

function createLogger() {
  fs.mkdirSync(LOG_DIR, { recursive: true });

  const transport = new DailyRotateFile({
    dirname: LOG_DIR,
    filename: "signum-%DATE%.log",
    datePattern: "YYYY-MM-DD",
    utc: true,
    maxSize: `${MAX_SIZE_MB}m`,
  });

  transport.on("rotate", (oldFile: string) => {
    zipAndRemove(oldFile)
      .then(cleanupOldArchives)
      .catch((err) => console.error("Log archive failure:", err));
  });

  zipStaleLogs().catch((err) => console.error("Log archive failure:", err));

  return winston.createLogger({
    level: LEVEL,
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.printf((info) => {
        const audit = info.audit ? "[AUDIT] " : "";
        const session = info.sessionId ?? "-";
        const msg = String(info.message).replace(/\r?\n/g, " ");
        return `[${info.timestamp}] [${String(info.level).toUpperCase()}] [${info.component}] ${audit}[${session}] ${msg}`;
      })
    ),
    transports: [transport],
  });
}

const globalForLogger = globalThis as unknown as { signumLogger?: winston.Logger };
const base = globalForLogger.signumLogger ?? createLogger();
if (process.env.NODE_ENV !== "production") globalForLogger.signumLogger = base;

export function log(
  level: LogLevel,
  component: LogComponent,
  message: string,
  opts: LogOptions = {}
) {
  base.log({
    level: level.toLowerCase(),
    message,
    component,
    audit: opts.audit ?? false,
    sessionId: opts.sessionId ?? null,
  });
}

export const logger = {
  debug: (c: LogComponent, m: string, o?: LogOptions) => log("DEBUG", c, m, o),
  info: (c: LogComponent, m: string, o?: LogOptions) => log("INFO", c, m, o),
  warn: (c: LogComponent, m: string, o?: LogOptions) => log("WARN", c, m, o),
  error: (c: LogComponent, m: string, o?: LogOptions) => log("ERROR", c, m, o),
};
