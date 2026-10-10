import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getUserId } from "@/lib/session-auth";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const session = await prisma.recognitionSession.findFirst({ where: { id, userId } });
  if (!session) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const captions = await prisma.caption.findMany({
    where: { sessionId: id },
    orderBy: { createdAt: "asc" },
  });
  return NextResponse.json(captions);
}
