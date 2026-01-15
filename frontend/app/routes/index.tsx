import { createFileRoute, Link } from "@tanstack/react-router";

import { CodebaseList } from "~/components/CodebaseList";
import { Button } from "~/components/ui/button";

export const Route = createFileRoute("/")({
  component: IndexRoute,
});

function IndexRoute() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header Section */}
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold">Code Documentation Assistant</h1>
        <p className="text-muted-foreground text-lg">
          Upload your codebase and ask questions about your code using AI
        </p>
        <div className="flex gap-4 justify-center">
          <Link to="/upload">
            <Button>Upload New Codebase</Button>
          </Link>
        </div>
      </div>

      {/* Codebase List */}
      <CodebaseList />
    </div>
  );
}
