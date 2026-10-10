import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getUserId } from "@/lib/session-auth";

export async function POST(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const session = await prisma.recognitionSession.create({ data: { userId } });
  return NextResponse.json(session, { status: 201 });
}

export async function GET(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const sessions = await prisma.recognitionSession.findMany({
    where: { userId },
    orderBy: { startedAt: "desc" },
    include: { _count: { select: { captions: true } } },
  });
  return NextResponse.json(sessions);
}
