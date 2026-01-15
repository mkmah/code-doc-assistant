import { createFileRoute } from "@tanstack/react-router";
import { ChatInterface } from "~/components/ChatInterface";

export const Route = createFileRoute("/chat/$codebaseId")({
  component: ChatRoute,
});

function ChatRoute() {
  const { codebaseId } = Route.useParams();

  return (
    <div className="container mx-auto py-8 h-screen flex flex-col">
      <header className="border-b pb-4 mb-4">
        <h1 className="text-2xl font-bold">Code Chat</h1>
        <p className="text-sm text-muted-foreground">Codebase ID: {codebaseId}</p>
      </header>

      <div className="flex-1 min-h-0">
        <ChatInterface codebaseId={codebaseId} />
      </div>
    </div>
  );
}
