import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface CodeViewerProps {
  code: string;
  language: string;
  filePath?: string;
  lineStart?: number;
  lineEnd?: number;
}

export function CodeViewer({ code, language, filePath, lineStart, lineEnd }: CodeViewerProps) {
  return (
    <Card className="w-full">
      {filePath && (
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-mono flex items-center justify-between">
            <span className="truncate">{filePath}</span>
            {lineStart && lineEnd && (
              <span className="text-xs text-muted-foreground">
                Lines {lineStart}-{lineEnd}
              </span>
            )}
          </CardTitle>
        </CardHeader>
      )}
      <CardContent className="pt-2">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          showLineNumbers
          startingLineNumber={lineStart}
          customStyle={{
            borderRadius: "0.375rem",
            margin: 0,
            fontSize: "0.875rem",
          }}
        >
          {code}
        </SyntaxHighlighter>
      </CardContent>
    </Card>
  );
}
