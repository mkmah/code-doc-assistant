import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircleIcon, ClockIcon, XCircleIcon, TrashIcon } from "@phosphor-icons/react";
import type { Codebase } from "@/lib/api";

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

interface CodebaseTableColumnsProps {
  onDelete: (codebase: Codebase) => void;
}

export function getCodebaseColumns({
  onDelete,
}: CodebaseTableColumnsProps): ColumnDef<Codebase>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const codebase = row.original;
        return (
          <div>
            <div className="font-medium">{codebase.name}</div>
            {codebase.description && (
              <div className="text-sm text-muted-foreground truncate max-w-xs">
                {codebase.description}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const codebase = row.original;
        return (
          <div className="space-y-1">
            {getStatusBadge(codebase.status)}
            {codebase.status === "processing" && codebase.progress !== undefined && (
              <div className="text-xs text-muted-foreground">{codebase.progress}%</div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "primary_language",
      header: "Language",
      cell: ({ row }) => {
        const codebase = row.original;
        return codebase.primary_language ? (
          <Badge variant="secondary" className="font-normal">
            {codebase.primary_language}
          </Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        );
      },
    },
    {
      accessorKey: "files",
      header: "Files",
      cell: ({ row }) => {
        const codebase = row.original;
        return (
          <span className="text-muted-foreground">
            {codebase.processed_files}/{codebase.total_files}
          </span>
        );
      },
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => {
        const codebase = row.original;
        return (
          <span className="text-muted-foreground">{formatDate(codebase.created_at)}</span>
        );
      },
    },
    {
      id: "actions",
      header: () => <div className="text-right">Actions</div>,
      cell: ({ row }) => {
        const codebase = row.original;
        return (
          <div className="text-right">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(codebase);
              }}
            >
              <TrashIcon className="h-4 w-4" />
            </Button>
          </div>
        );
      },
    },
  ];
}
