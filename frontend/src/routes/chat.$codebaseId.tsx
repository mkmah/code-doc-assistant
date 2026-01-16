import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeftIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatInterface } from "@/components/ChatInterface";

export const Route = createFileRoute("/chat/$codebaseId")({
  component: ChatRoute,
});

function ChatRoute() {
  const { codebaseId } = Route.useParams();

  return (
    <div className="container mx-auto py-8 h-screen flex flex-col">
      <header className="border-b pb-4 mb-4">
        <div className="flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="icon" className="shrink-0">
              <ArrowLeftIcon className="h-5 w-5" />
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">Code Chat</h1>
            <p className="text-sm text-muted-foreground">Codebase ID: {codebaseId}</p>
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 pb-6">
        <ChatInterface codebaseId={codebaseId} />
      </div>
    </div>
  );
}
