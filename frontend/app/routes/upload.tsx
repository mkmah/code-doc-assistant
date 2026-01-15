import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { UploadForm } from "~/components/UploadForm";
import { StatusTracker } from "~/components/StatusTracker";

export const Route = createFileRoute("/upload")({
  component: UploadRoute,
});

function UploadRoute() {
  const navigate = Route.useNavigate();
  const [ingestingCodebaseId, setIngestingCodebaseId] = useState<string | null>(null);

  const handleUploadSuccess = (codebaseId: string) => {
    setIngestingCodebaseId(codebaseId);
  };

  const handleIngestionComplete = () => {
    if (ingestingCodebaseId) {
      navigate({ to: `/chat/${ingestingCodebaseId}` });
    }
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">Upload Codebase</h1>

      {!ingestingCodebaseId ? (
        <UploadForm onSuccess={handleUploadSuccess} />
      ) : (
        <div className="max-w-2xl mx-auto">
          <StatusTracker
            codebaseId={ingestingCodebaseId}
            onComplete={handleIngestionComplete}
          />
        </div>
      )}
    </div>
  );
}
