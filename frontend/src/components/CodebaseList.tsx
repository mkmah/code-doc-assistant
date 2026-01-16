import { useState } from "react";
import { EmptyState } from "./EmptyState";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { useCodebaseList } from "@/hooks/useCodebaseList";
import { useDeleteCodebase } from "@/hooks/useDeleteCodebase";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { getCodebaseColumns } from "./codebase-columns";
import { ArrowClockwise, Spinner } from "@phosphor-icons/react";
import type { Codebase } from "@/lib/api";

const PAGE_SIZE = 10;

export function CodebaseList() {
  const [page, setPage] = useState(1);
  const { data, isLoading, error, refetch } = useCodebaseList({ page, limit: PAGE_SIZE });
  const { deleteCodebase } = useDeleteCodebase();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [codebaseToDelete, setCodebaseToDelete] = useState<Codebase | null>(null);

  const codebases = data?.codebases || [];
  const totalCount = data?.total ?? 0;

  const handleDeleteClick = (codebase: Codebase) => {
    setCodebaseToDelete(codebase);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (codebaseToDelete) {
      deleteCodebase(codebaseToDelete.id);
      setDeleteDialogOpen(false);
      setCodebaseToDelete(null);
    }
  };

  const handleRowClick = (codebase: Codebase) => {
    if (codebase.status === "completed") {
      window.location.href = `/chat/${codebase.id}`;
    }
  };

  const handleNextPage = () => {
    setPage((p) => p + 1);
  };

  const handlePreviousPage = () => {
    setPage((p) => Math.max(1, p - 1));
  };

  const columns = getCodebaseColumns({ onDelete: handleDeleteClick });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-muted-foreground">Loading codebases...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="text-center max-w-md">
          <h3 className="text-lg font-semibold text-destructive mb-2">
            Failed to load codebases
          </h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
          <Button onClick={() => refetch()} variant="outline">
            <ArrowClockwise className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (codebases.length === 0 && page === 1) {
    return <EmptyState />;
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">
            Your Codebases ({totalCount})
          </h2>
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <ArrowClockwise className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        <DataTable
          columns={columns}
          data={codebases}
          pageSize={PAGE_SIZE}
          currentPage={page}
          totalCount={totalCount}
          onNextPage={handleNextPage}
          onPreviousPage={handlePreviousPage}
          onRowClick={handleRowClick}
          isRowClickable={(codebase) => codebase.status === "completed"}
        />
      </div>

      {codebaseToDelete && (
        <DeleteConfirmDialog
          isOpen={deleteDialogOpen}
          onClose={() => {
            setDeleteDialogOpen(false);
            setCodebaseToDelete(null);
          }}
          onConfirm={handleDeleteConfirm}
          codebaseName={codebaseToDelete.name}
        />
      )}
    </>
  );
}
