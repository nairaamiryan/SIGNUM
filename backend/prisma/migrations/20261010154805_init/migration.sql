-- CreateEnum
CREATE TYPE "SessionStatus" AS ENUM ('ACTIVE', 'ENDED');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "passwordHash" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RecognitionSession" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "status" "SessionStatus" NOT NULL DEFAULT 'ACTIVE',
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endedAt" TIMESTAMP(3),

    CONSTRAINT "RecognitionSession_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RecognizedGesture" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "gloss" TEXT NOT NULL,
    "classId" INTEGER,
    "confidence" DOUBLE PRECISION NOT NULL,
    "landmarkData" JSONB,
    "recognizedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RecognizedGesture_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Caption" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "text" TEXT NOT NULL,
    "glosses" TEXT[],
    "confidence" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Caption_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "RecognitionSession_userId_idx" ON "RecognitionSession"("userId");

-- CreateIndex
CREATE INDEX "RecognizedGesture_sessionId_idx" ON "RecognizedGesture"("sessionId");

-- CreateIndex
CREATE INDEX "Caption_sessionId_idx" ON "Caption"("sessionId");

-- AddForeignKey
ALTER TABLE "RecognitionSession" ADD CONSTRAINT "RecognitionSession_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RecognizedGesture" ADD CONSTRAINT "RecognizedGesture_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "RecognitionSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Caption" ADD CONSTRAINT "Caption_sessionId_fkey" FOREIGN KEY ("sessionId") REFERENCES "RecognitionSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;
