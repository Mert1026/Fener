import Link from "next/link";
import { LockKeyhole } from "lucide-react";
export function PrivateGate() {
  return (
    <div className="info-callout">
      <LockKeyhole size={20} />
      <div>
        <strong>This is your private intelligence.</strong>Unlock the workspace
        to run cited research and manage source syncs. These records are never
        part of the public model catalog.
        <br />
        <Link
          href="/settings"
          className="button primary"
          style={{ marginTop: 15 }}
        >
          Unlock workspace →
        </Link>
      </div>
    </div>
  );
}
