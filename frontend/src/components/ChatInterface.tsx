import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Card, CardContent } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { chatCodebase } from "@/lib/api";
import { CodeViewer } from "./CodeViewer";
import { Markdown } from "./Markdown";

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
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Code viewer modal state
  const [codeViewerOpen, setCodeViewerOpen] = useState(false);
  const [codeViewerCode, setCodeViewerCode] = useState("");
  const [codeViewerLanguage, setCodeViewerLanguage] = useState("");
  const [codeViewerFilePath, setCodeViewerFilePath] = useState("");
  const [codeViewerLineStart, setCodeViewerLineStart] = useState<number>(0);
  const [codeViewerLineEnd, setCodeViewerLineEnd] = useState<number>(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleCitationClick = async (
    filePath: string,
    lineStart: number,
    lineEnd: number
  ) => {
    try {
      // Fetch the code snippet from the backend
      // TODO: this api can be created to show the snippets
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/codebase/${codebaseId}/snippet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: filePath, line_start: lineStart, line_end: lineEnd }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch code snippet");
      }

      const data = await response.json();
      setCodeViewerCode(data.code || "");
      setCodeViewerLanguage(data.language || "text");
      setCodeViewerFilePath(filePath);
      setCodeViewerLineStart(lineStart);
      setCodeViewerLineEnd(lineEnd);
      setCodeViewerOpen(true);
    } catch (err) {
      console.error("Failed to load code snippet:", err);
      // Show a simple error message to the user
      setError("Failed to load code snippet. Please try again.");
    }
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

      // Pass session_id if available (for follow-up requests)
      for await (const event of chatCodebase({
        codebase_id: codebaseId,
        query,
        session_id: sessionId,
      })) {
        if (event.type === "session_id" && event.session_id) {
          // Store session_id for follow-up requests
          setSessionId(event.session_id);
        } else if (event.type === "chunk") {
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
                  {message.role === "assistant" ? (
                    <Markdown content={message.content} />
                  ) : (
                    <div className="whitespace-pre-wrap break-words">
                      {message.content}
                    </div>
                  )}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-xs font-semibold mb-2">Sources:</p>
                      <div className="flex flex-wrap gap-2">
                        {message.sources.map((source, i) => (
                          <button
                            key={i}
                            type="button"
                            // onClick={() =>
                            //   handleCitationClick(
                            //     source.file_path,
                            //     source.line_start,
                            //     source.line_end
                            //   )
                            // }
                            className="text-xs bg-background hover:bg-accent px-2 py-1 rounded transition-colors cursor-pointer"
                            title="Click to view code"
                          >
                            <code className="text-xs">
                              {source.file_path}:{source.line_start}-{source.line_end}
                            </code>
                          </button>
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
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse delay-75" />
                    <span className="w-2 h-2 bg-primary rounded-full animate-pulse delay-150" />
                  </div>
                  <span className="text-sm text-muted-foreground">
                    AI is thinking...
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
      <div className="pt-4 border-t">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your code..."
            disabled={isLoading}
            className="flex-1 min-h-[100px] max-h-[200px] resize-y"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (query.trim() && !isLoading) {
                  handleSubmit(e);
                }
              }
            }}
          />
          <Button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="h-[100px] px-6"
          >
            Send
          </Button>
        </form>
      </div>

      {/* Code Viewer Modal */}
      <Dialog open={codeViewerOpen} onOpenChange={setCodeViewerOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Code Viewer</DialogTitle>
          </DialogHeader>
          <CodeViewer
            code={codeViewerCode}
            language={codeViewerLanguage}
            filePath={codeViewerFilePath}
            lineStart={codeViewerLineStart}
            lineEnd={codeViewerLineEnd}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
