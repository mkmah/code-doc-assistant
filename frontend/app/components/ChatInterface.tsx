import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { chatCodebase, type StreamEvent } from "~/lib/api";

interface ChatInterfaceProps {
  codebaseId: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    file_path: string;
    line_start: number;
    line_end: number;
    snippet?: string;
  }>;
}

export function ChatInterface({ codebaseId }: ChatInterfaceProps) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setError(null);
    setIsLoading(true);

    // Add placeholder for assistant message
    const assistantIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      let accumulatedContent = "";
      let sources: Array<{
        file_path: string;
        line_start: number;
        line_end: number;
        snippet?: string;
      }> = [];

      for await (const event of chatCodebase({ codebase_id: codebaseId, query })) {
        if (event.type === "chunk") {
          accumulatedContent += event.content || "";
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[assistantIndex] = {
              role: "assistant",
              content: accumulatedContent,
            };
            return newMessages;
          });
        } else if (event.type === "sources") {
          sources = event.sources || [];
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[assistantIndex] = {
              role: "assistant",
              content: accumulatedContent,
              sources,
            };
            return newMessages;
          });
        } else if (event.type === "error") {
          setError(event.error || "An error occurred");
          break;
        } else if (event.type === "done") {
          break;
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to send message");
      // Remove the placeholder assistant message
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-lg mb-2">Ask a question about your code</p>
            <p className="text-sm">
              Try: "How does authentication work?" or "What are the main functions?"
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <Card
                className={`max-w-[80%] ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <CardContent className="p-4">
                  <div className="whitespace-pre-wrap break-words">
                    {message.content}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-xs font-semibold mb-2">Sources:</p>
                      <div className="space-y-1">
                        {message.sources.map((source, i) => (
                          <div
                            key={i}
                            className="text-xs bg-background p-2 rounded"
                          >
                            <code className="text-xs">
                              {source.file_path}:{source.line_start}-{source.line_end}
                            </code>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <Card className="bg-muted max-w-[80%]">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                  <span className="text-sm text-muted-foreground">
                    Thinking...
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about your code..."
          disabled={isLoading}
          className="flex-1"
        />
        <Button type="submit" disabled={isLoading || !query.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
