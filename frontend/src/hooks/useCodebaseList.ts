import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listCodebases } from "@/lib/api";

interface UseCodebaseListParams {
  page?: number;
  limit?: number;
}

export function useCodebaseList({ page = 1, limit = 5 }: UseCodebaseListParams = {}) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["codebases", page, limit],
    queryFn: () => listCodebases(page, limit),
    staleTime: 5000, // 5 seconds
  });

  const refetch = () => {
    void queryClient.invalidateQueries({ queryKey: ["codebases"] });
  };

  return {
    ...query,
    refetch,
  };
}
