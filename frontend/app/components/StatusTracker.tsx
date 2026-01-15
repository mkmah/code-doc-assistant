import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { getCodebaseStatus, type IngestionStatus } from "~/lib/api";

interface StatusTrackerProps {
  codebaseId: string;
  onComplete?: () => void;
}

export function StatusTracker({ codebaseId, onComplete }: StatusTrackerProps) {
  const [status, setStatus] = useState<IngestionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    const fetchStatus = async () => {
      try {
        const result = await getCodebaseStatus(codebaseId);
        setStatus(result);

        // Stop polling if complete or failed
        if (result.status === "completed" || result.status === "failed") {
          if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
          }
          if (result.status === "completed" && onComplete) {
            onComplete();
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch status");
        if (intervalId) {
          clearInterval(intervalId);
        }
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 2 seconds
    intervalId = setInterval(fetchStatus, 2000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [codebaseId, onComplete]);

  if (!status) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="flex items-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
            <span className="text-sm">Loading status...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStepColor = (step: string | null) => {
    if (!step) return "bg-muted";
    const steps = ["validating", "cloning", "parsing", "chunking", "embedding", "indexing", "complete"];
    const currentIndex = steps.indexOf(status.current_step || "");
    const stepIndex = steps.indexOf(step || "");
    if (stepIndex < currentIndex) return "bg-green-500";
    if (stepIndex === currentIndex) return "bg-blue-500 animate-pulse";
    return "bg-muted";
  };

  const getStepLabel = (step: string) => {
    const labels: Record<string, string> = {
      validating: "Validating",
      cloning: "Cloning/Extracting",
      parsing: "Parsing Code",
      chunking: "Creating Chunks",
      embedding: "Generating Embeddings",
      indexing: "Indexing",
      complete: "Complete",
    };
    return labels[step] || step;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Ingestion Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Progress</span>
            <span>{status.progress.toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${status.progress}%` }}
            />
          </div>
        </div>

        {/* Step Indicators */}
        <div className="space-y-2">
          <p className="text-sm font-medium">Processing Steps</p>
          <div className="grid grid-cols-4 gap-2">
            {["validating", "cloning", "parsing", "chunking", "embedding", "indexing", "complete"].map((step) => (
              <div key={step} className="flex flex-col items-center gap-1">
                <div
                  className={`h-2 w-full rounded-full ${getStepColor(step)}`}
                />
                <span className="text-xs text-center">{getStepLabel(step)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* File Count */}
        <div className="text-sm">
          <span className="text-muted-foreground">Files: </span>
          <span className="font-medium">
            {status.processed_files} / {status.total_files}
          </span>
        </div>

        {/* Secrets Detected */}
        {status.secrets_detected && status.secrets_detected.length > 0 && (
          <div className="p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
            <p className="text-sm font-medium mb-1">Secrets Detected</p>
            <ul className="text-xs space-y-1">
              {status.secrets_detected.map((d, i) => (
                <li key={i} className="text-muted-foreground">
                  {d.file_path}: {d.secret_count} secret(s)
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Error */}
        {status.status === "failed" && status.error && (
          <div className="p-3 rounded-md bg-destructive/10 text-destructive">
            <p className="text-sm font-medium">Error:</p>
            <p className="text-xs mt-1">{status.error}</p>
          </div>
        )}

        {/* Completion Message */}
        {status.status === "completed" && (
          <div className="p-3 rounded-md bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Codebase successfully processed!
            </p>
            {status.primary_language && (
              <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                Primary language: {status.primary_language}
              </p>
            )}
          </div>
        )}

        {error && (
          <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
