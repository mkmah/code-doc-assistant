import type { Codebase } from "@/lib/api";

export interface CodebaseListProps {
  codebases: Codebase[];
  isLoading: boolean;
  error: string | null;
  onDeleteCodebase: (codebaseId: string) => Promise<void>;
}
