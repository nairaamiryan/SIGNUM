import { RecognitionSession, Caption } from "@/lib/db";

export async function createSession(userId: string) {
  return RecognitionSession.create({ userId });
}

export async function listSessionsWithCaptionCount(userId: string) {
  const sessions = await RecognitionSession.findAll({
    where: { userId },
    order: [["startedAt", "DESC"]],
  });
  return Promise.all(
    sessions.map(async (s) => ({
      ...s.get(),
      captionCount: await Caption.count({ where: { sessionId: s.get("id") as string } }),
    }))
  );
}

export async function findSessionById(id: string) {
  return RecognitionSession.findByPk(id);
}

export async function findUserSession(id: string, userId: string) {
  return RecognitionSession.findOne({ where: { id, userId } });
}

export async function endUserSession(id: string, userId: string) {
  const [count] = await RecognitionSession.update(
    { status: "ENDED", endedAt: new Date() },
    { where: { id, userId } }
  );
  return count > 0;
}
