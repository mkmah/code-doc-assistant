import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface CodeViewerProps {
  code: string;
  language: string;
  filePath?: string;
  lineStart?: number;
  lineEnd?: number;
}

export function CodeViewer({ code, language, filePath, lineStart, lineEnd }: CodeViewerProps) {
  // Simple syntax highlighting (for MVP)
  // In production, would use shiki or prism.js
  const highlightCode = (code: string, lang: string) => {
    // Escape HTML
    let escaped = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Basic syntax highlighting
    if (lang === "python" || lang === "python") {
      // Keywords
      escaped = escaped.replace(
        /\b(def|class|if|else|elif|for|while|return|import|from|as|try|except|raise|with|lambda|True|False|None)\b/g,
        '<span class="text-purple-600">$1</span>'
      );
      // Strings
      escaped = escaped.replace(/(["'])(?:(?!\1)[^\\]|\\.)*?\1/g, '<span class="text-green-600">$&</span>');
      // Comments
      escaped = escaped.replace(/#.*$/gm, '<span class="text-gray-500">$&</span>');
    } else if (lang === "javascript" || lang === "typescript" || lang === "js" || lang === "ts") {
      // Keywords
      escaped = escaped.replace(
        /\b(const|let|var|function|return|if|else|for|while|do|switch|case|break|continue|new|this|class|extends|import|export|from|async|await|try|catch|throw|true|false|null|undefined)\b/g,
        '<span class="text-purple-600">$1</span>'
      );
      // Strings
      escaped = escaped.replace(/(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g, '<span class="text-green-600">$&</span>');
      // Comments
      escaped = escaped.replace(/(\/\/.*$)/gm, '<span class="text-gray-500">$1</span>');
      escaped = escaped.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="text-gray-500">$1</span>');
    }

    return escaped;
  };

  return (
    <Card className="w-full">
      {filePath && (
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-mono flex items-center justify-between">
            <span>{filePath}</span>
            {lineStart && lineEnd && (
              <span className="text-xs text-muted-foreground">
                Lines {lineStart}-{lineEnd}
              </span>
            )}
          </CardTitle>
        </CardHeader>
      )}
      <CardContent className="pt-2">
        <pre className="bg-muted p-4 rounded-md overflow-x-auto">
          <code
            className="text-sm"
            dangerouslySetInnerHTML={{
              __html: highlightCode(code, language),
            }}
          />
        </pre>
      </CardContent>
    </Card>
  );
}
