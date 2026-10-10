import { verifyToken } from "@/lib/auth";

export function getUserId(req: Request): string | null {
  const header = req.headers.get("authorization");
  if (!header?.startsWith("Bearer ")) return null;
  const payload = verifyToken(header.slice(7));
  return payload?.sub ?? null;
}
