import { Caption, RecognizedGesture } from "@/lib/db";

export async function listCaptions(sessionId: string) {
  return Caption.findAll({ where: { sessionId }, order: [["createdAt", "ASC"]] });
}

export async function createCaption(
  sessionId: string,
  data: { text: string; glosses: string[]; confidence?: number }
) {
  return Caption.create({ sessionId, ...data });
}

export async function createGesture(
  sessionId: string,
  data: { gloss: string; classId?: number; confidence: number; landmarkData?: unknown }
) {
  return RecognizedGesture.create({ sessionId, ...data });
}
