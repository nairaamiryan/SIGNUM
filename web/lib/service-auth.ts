export function isServiceRequest(req: Request): boolean {
  const key = process.env.SERVICE_API_KEY;
  return !!key && req.headers.get("x-service-key") === key;
}
