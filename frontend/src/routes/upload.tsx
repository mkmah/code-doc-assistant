import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeftIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UploadForm } from "@/components/UploadForm";
import { StatusTracker } from "@/components/StatusTracker";

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
      void navigate({ to: `/chat/${ingestingCodebaseId}` });
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex items-center gap-4 mb-8">
        <Link to="/">
          <Button variant="ghost" size="icon" className="shrink-0">
            <ArrowLeftIcon className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-3xl font-bold">Upload Codebase</h1>
      </div>

      {!ingestingCodebaseId ? (
        <UploadForm onSuccess={handleUploadSuccess} />
      ) : (
        <StatusTracker codebaseId={ingestingCodebaseId} onComplete={handleIngestionComplete} />
      )}
    </div>
  );
}
