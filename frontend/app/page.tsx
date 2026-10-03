import CameraFeed from "@/components/CameraFeed";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 gap-6">
      <h1 className="text-2xl font-bold">ArSL Recognition — Camera Test</h1>
      <CameraFeed />
    </main>
  );
}