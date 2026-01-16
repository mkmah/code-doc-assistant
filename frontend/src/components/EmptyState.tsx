import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UploadIcon, FileCodeIcon } from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";

interface EmptyStateProps {
  title?: string;
  description?: string;
}

export function EmptyState({
  title = "No codebases yet",
  description = "Upload your first codebase to start asking questions about your code.",
}: EmptyStateProps) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
          <FileCodeIcon className="h-8 w-8 text-primary" />
        </div>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground mb-6 max-w-md">{description}</p>
        <Link to="/upload">
          <Button className="gap-2" size="lg">
            <UploadIcon className="h-5 w-5" />
            Upload Your First Codebase
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
