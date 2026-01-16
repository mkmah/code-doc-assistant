"""Code parsing utilities using Tree-sitter."""

from pathlib import Path
from typing import Any

import tree_sitter_languages as tsl
from pydantic import BaseModel
from tree_sitter import Language, Node, Parser

from app.core.logging import get_logger

logger = get_logger(__name__)


# Supported languages and their Tree-sitter identifiers
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}


class ParsedCode(BaseModel):
    """Result of parsing a code file."""

    file_path: str
    language: str
    functions: list[dict[str, Any]]
    classes: list[dict[str, Any]]
    imports: list[dict[str, Any]]
    docstring: str | None = None
    complexity: int = 0


class CodeParser:
    """Multi-language code parser using Tree-sitter."""

    def __init__(self) -> None:
        """Initialize the code parser with language support."""
        self._parsers: dict[str, Parser] = {}
        self._languages: dict[str, Language] = {}

    def _get_parser(self, language: str) -> Parser:
        """Get or create a parser for the given language.

        Args:
            language: Language name (e.g., "python")

        Returns:
            Tree-sitter parser instance
        """
        if language not in self._parsers:
            try:
                lang_obj = tsl.get_language(language)
                parser = Parser()
                parser.set_language(lang_obj)
                self._parsers[language] = parser
                self._languages[language] = lang_obj
                logger.debug("parser_created", language=language)
            except Exception as e:
                logger.warning("parser_language_not_supported", language=language, error=str(e))
                raise ValueError(f"Unsupported language: {language}")

        return self._parsers[language]

    @staticmethod
    def detect_language(file_path: str) -> str | None:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if not detected
        """
        ext = Path(file_path).suffix.lower()
        return LANGUAGE_MAP.get(ext)

    def parse_file(self, file_path: str, content: str) -> ParsedCode:
        """Parse a code file and extract semantic information.

        Args:
            file_path: Path to the file (for language detection)
            content: File content to parse

        Returns:
            ParsedCode with extracted information

        Raises:
            ValueError: If language is not supported
        """
        language = self.detect_language(file_path)
        if not language:
            raise ValueError(f"Cannot detect language for {file_path}")

        try:
            parser = self._get_parser(language)
            tree = parser.parse(bytes(content, "utf-8"))
        except Exception as e:
            logger.warning("parse_failed", file_path=file_path, error=str(e))
            # Return empty result on parse failure
            return ParsedCode(
                file_path=file_path,
                language=language,
                functions=[],
                classes=[],
                imports=[],
            )

        # Extract information from AST
        functions = self._extract_functions(tree.root_node, content, language)
        classes = self._extract_classes(tree.root_node, content, language)
        imports = self._extract_imports(tree.root_node, content, language)

        # Calculate complexity
        complexity = len(functions) + len(classes) * 2

        return ParsedCode(
            file_path=file_path,
            language=language,
            functions=functions,
            classes=classes,
            imports=imports,
            complexity=complexity,
        )

    def _extract_functions(
        self,
        root: Node,
        content: str,
        language: str,
    ) -> list[dict[str, Any]]:
        """Extract function definitions from AST.

        Args:
            root: Root AST node
            content: Source code content
            language: Programming language

        Returns:
            List of function metadata
        """
        functions = []

        # Language-specific node types for functions
        function_node_types = {
            "python": ["function_definition", "lambda"],
            "javascript": ["function_declaration", "function_expression", "arrow_function"],
            "typescript": ["function_declaration", "function_expression", "arrow_function"],
            "java": ["method_declaration"],
            "go": ["function_declaration", "method_declaration"],
            "rust": ["function_item"],
        }

        node_types = function_node_types.get(language, [])

        def extract_recursive(node: Node) -> None:
            if node.type in node_types:
                func_info = self._extract_function_info(node, content)
                if func_info:
                    functions.append(func_info)

            for child in node.children:
                extract_recursive(child)

        extract_recursive(root)
        return functions

    def _extract_function_info(self, node: Node, content: str) -> dict[str, Any] | None:
        """Extract metadata from a function node.

        Args:
            node: Function AST node
            content: Source code content

        Returns:
            Function metadata dict or None
        """
        try:
            # Get function name from the first child that's an identifier
            name = None
            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                    break

            if not name:
                return None

            # Get docstring (if present) - varies by language
            docstring = None
            # This would need language-specific logic

            return {
                "name": name,
                "line_start": node.start_point[0] + 1,  # 1-indexed
                "line_end": node.end_point[0] + 1,
                "byte_start": node.start_byte,
                "byte_end": node.end_byte,
                "docstring": docstring,
            }
        except Exception as e:
            logger.warning("function_extraction_failed", error=str(e))
            return None

    def _extract_classes(
        self,
        root: Node,
        content: str,
        language: str,
    ) -> list[dict[str, Any]]:
        """Extract class definitions from AST.

        Args:
            root: Root AST node
            content: Source code content
            language: Programming language

        Returns:
            List of class metadata
        """
        classes = []

        # Language-specific node types for classes
        class_node_types = {
            "python": ["class_definition"],
            "javascript": ["class_declaration"],
            "typescript": ["class_declaration", "interface_declaration"],
            "java": ["class_declaration", "interface_declaration"],
            "go": ["type_declaration"],  # For structs
            "rust": ["impl_item", "struct_item"],
        }

        node_types = class_node_types.get(language, [])

        def extract_recursive(node: Node) -> None:
            if node.type in node_types:
                class_info = self._extract_class_info(node, content)
                if class_info:
                    classes.append(class_info)

            for child in node.children:
                extract_recursive(child)

        extract_recursive(root)
        return classes

    def _extract_class_info(self, node: Node, content: str) -> dict[str, Any] | None:
        """Extract metadata from a class node.

        Args:
            node: Class AST node
            content: Source code content

        Returns:
            Class metadata dict or None
        """
        try:
            # Get class name from the first child that's an identifier
            name = None
            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                    break

            if not name:
                return None

            return {
                "name": name,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "byte_start": node.start_byte,
                "byte_end": node.end_byte,
            }
        except Exception as e:
            logger.warning("class_extraction_failed", error=str(e))
            return None

    def _extract_imports(
        self,
        root: Node,
        content: str,
        language: str,
    ) -> list[dict[str, Any]]:
        """Extract import statements from AST.

        Args:
            root: Root AST node
            content: Source code content
            language: Programming language

        Returns:
            List of import metadata
        """
        imports = []

        # Language-specific node types for imports
        import_node_types = {
            "python": ["import_statement", "import_from_statement"],
            "javascript": ["import_statement", "require"],
            "typescript": ["import_statement", "require"],
            "java": ["import_declaration"],
            "go": ["import_declaration"],
        }

        node_types = import_node_types.get(language, [])

        def extract_recursive(node: Node) -> None:
            if node.type in node_types:
                import_text = content[node.start_byte : node.end_byte].strip()
                imports.append(
                    {
                        "text": import_text,
                        "line": node.start_point[0] + 1,
                    }
                )

            for child in node.children:
                extract_recursive(child)

        extract_recursive(root)
        return imports


# Singleton instance
_code_parser: CodeParser | None = None


def get_code_parser() -> CodeParser:
    """Get the singleton code parser instance."""
    global _code_parser
    if _code_parser is None:
        _code_parser = CodeParser()
    return _code_parser
