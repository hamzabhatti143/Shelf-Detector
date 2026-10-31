import type { Metadata } from "next";
import { CameraAudit } from "@/components/audit/CameraAudit";

export const metadata: Metadata = { title: "Camera audit" };

export default function CameraPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Camera audit</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Connect a store camera, check the picture, then audit the shelf it sees.
        </p>
      </div>
      <CameraAudit />
    </div>
  );
}