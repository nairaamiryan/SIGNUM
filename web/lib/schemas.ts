import { z } from "zod";

export const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().optional(),
});

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

export const updateUserSchema = z.object({
  name: z.string().min(1).max(100),
});

export const captionSchema = z.object({
  text: z.string().min(1),
  glosses: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1).optional(),
});

export const gestureSchema = z.object({
  gloss: z.string().min(1),
  classId: z.number().int().optional(),
  confidence: z.number().min(0).max(1),
  landmarkData: z.any().optional(),
});
