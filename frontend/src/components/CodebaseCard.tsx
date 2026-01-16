import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrashIcon, FileCodeIcon, ClockIcon, CheckCircleIcon, XCircleIcon } from "@phosphor-icons/react";
import type { Codebase } from "@/lib/api";

interface CodebaseCardProps {
  codebase: Codebase;
  onDelete: (codebaseId: string) => void;
}

function getStatusBadge(status: Codebase["status"]) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="outline" className="gap-1.5 text-green-600 border-green-600">
          <CheckCircleIcon className="h-3 w-3" />
          Completed
        </Badge>
      );
    case "processing":
    case "queued":
      return (
        <Badge variant="outline" className="gap-1.5 text-yellow-600 border-yellow-600">
          <ClockIcon className="h-3 w-3" />
          Processing
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="outline" className="gap-1.5 text-red-600 border-red-600">
          <XCircleIcon className="h-3 w-3" />
          Failed
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function CodebaseCard({ codebase, onDelete }: CodebaseCardProps) {
  const handleClick = () => {
    if (codebase.status === "completed") {
      // Navigate to chat
      window.location.href = `/chat/${codebase.id}`;
    }
  };

  return (
    <Card
      className={`
        group relative transition-all duration-200
        ${codebase.status === "completed" ? "hover:border-primary hover:shadow-md cursor-pointer" : ""}
        ${codebase.status === "failed" ? "border-red-200" : ""}
      `}
      onClick={handleClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileCodeIcon className="h-5 w-5 text-muted-foreground" />
            <span className="truncate flex-1">{codebase.name}</span>
          </CardTitle>
          {getStatusBadge(codebase.status)}
        </div>
        {codebase.description && (
          <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
            {codebase.description}
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-2">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          {codebase.primary_language && (
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">Language:</span>
              <Badge variant="secondary" className="font-normal">
                {codebase.primary_language}
              </Badge>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Files:</span>
            <span className="font-medium">
              {codebase.processed_files}/{codebase.total_files}
            </span>
          </div>
        </div>

        {codebase.status === "processing" && codebase.progress !== undefined && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{codebase.progress}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${codebase.progress}%` }}
              />
            </div>
          </div>
        )}

        {codebase.error_message && (
          <div className="text-sm text-red-600 bg-red-50 dark:bg-red-950/20 rounded px-2 py-1">
            {codebase.error_message}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex items-center justify-between pt-3 border-t">
        <div className="text-xs text-muted-foreground">
          {formatDate(codebase.created_at)}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 text-destructive hover:text-destructive hover:bg-destructive/10"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(codebase.id);
          }}
        >
          <TrashIcon className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
