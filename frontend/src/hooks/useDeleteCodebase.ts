import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteCodebase } from "@/lib/api";
import type { Codebase } from "@/lib/api";

export function useDeleteCodebase() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (codebaseId: string) => deleteCodebase(codebaseId),
    onMutate: async (codebaseId: string) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["codebases"] });

      // Snapshot previous value
      const previousCodebases = queryClient.getQueryData<{ codebases: Codebase[] }>(["codebases"]);

      // Optimistically update to the new value
      queryClient.setQueryData<{ codebases: Codebase[] }>(["codebases"], (old) => ({
        codebases: old?.codebases.filter((cb) => cb.id !== codebaseId) || [],
      }));

      // Return context with previous value
      return { previousCodebases };
    },
    onError: (_err, _codebaseId, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousCodebases) {
        queryClient.setQueryData<{ codebases: Codebase[] }>(
          ["codebases"],
          context.previousCodebases,
        );
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      void queryClient.invalidateQueries({ queryKey: ["codebases"] });
    },
  });

  return {
    deleteCodebase: mutation.mutate,
    isDeleting: mutation.isPending,
  };
}
