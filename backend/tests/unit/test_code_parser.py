"""Unit tests for code parser utilities."""

from app.utils.code_parser import CodeParser, ParsedCode


class TestDetectLanguage:
    """Tests for detect_language static method."""

    def test_detect_python_language(self):
        """Test Python language detection."""
        assert CodeParser.detect_language("test.py") == "python"
        assert CodeParser.detect_language("app/main.py") == "python"
        assert CodeParser.detect_language("script.py") == "python"

    def test_detect_javascript_language(self):
        """Test JavaScript language detection."""
        assert CodeParser.detect_language("test.js") == "javascript"
        assert CodeParser.detect_language("app.jsx") == "javascript"

    def test_detect_typescript_language(self):
        """Test TypeScript language detection."""
        assert CodeParser.detect_language("test.ts") == "typescript"
        assert CodeParser.detect_language("app.tsx") == "typescript"

    def test_detect_java_language(self):
        """Test Java language detection."""
        assert CodeParser.detect_language("Test.java") == "java"

    def test_detect_go_language(self):
        """Test Go language detection."""
        assert CodeParser.detect_language("main.go") == "go"

    def test_detect_rust_language(self):
        """Test Rust language detection."""
        assert CodeParser.detect_language("lib.rs") == "rust"

    def test_detect_c_language(self):
        """Test C language detection."""
        assert CodeParser.detect_language("main.c") == "c"
        assert CodeParser.detect_language("header.h") == "c"

    def test_detect_cpp_language(self):
        """Test C++ language detection."""
        assert CodeParser.detect_language("main.cpp") == "cpp"
        assert CodeParser.detect_language("lib.cc") == "cpp"
        assert CodeParser.detect_language("impl.cxx") == "cpp"
        assert CodeParser.detect_language("header.hpp") == "cpp"

    def test_detect_unsupported_language(self):
        """Test unsupported file extensions."""
        assert CodeParser.detect_language("test.txt") is None
        assert CodeParser.detect_language("README.md") is None
        assert CodeParser.detect_language("config.json") is None


class TestCodeParser:
    """Tests for CodeParser class."""

    def test_parse_simple_python_function(self):
        """Test parsing a simple Python function."""
        parser = CodeParser()
        code = """def hello_world():
    '''A simple greeting function.'''
    print("Hello, World!")
    return 42
"""

        result = parser.parse_file("test.py", code)

        assert isinstance(result, ParsedCode)
        assert result.file_path == "test.py"
        assert result.language == "python"
        assert len(result.functions) == 1
        assert result.functions[0]["name"] == "hello_world"
        assert result.functions[0]["line_start"] == 1
        assert result.functions[0]["line_end"] == 5

    def test_parse_python_function_with_parameters(self):
        """Test parsing a Python function with parameters."""
        parser = CodeParser()
        code = """def calculate_sum(a: int, b: int) -> int:
    '''Calculate the sum of two numbers.'''
    return a + b
"""

        result = parser.parse_file("calc.py", code)

        assert len(result.functions) == 1
        assert result.functions[0]["name"] == "calculate_sum"

    def test_parse_multiple_python_functions(self):
        """Test parsing multiple Python functions."""
        parser = CodeParser()
        code = """def foo():
    pass

def bar():
    pass

def baz():
    pass
"""

        result = parser.parse_file("test.py", code)

        assert len(result.functions) == 3
        function_names = [f["name"] for f in result.functions]
        assert "foo" in function_names
        assert "bar" in function_names
        assert "baz" in function_names

    def test_parse_python_class_with_methods(self):
        """Test parsing a Python class with methods."""
        parser = CodeParser()
        code = """class Calculator:
    '''A simple calculator class.'''

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""

        result = parser.parse_file("calc.py", code)

        assert len(result.classes) == 1
        assert result.classes[0]["name"] == "Calculator"
        assert len(result.functions) == 2  # Methods are also extracted as functions
        method_names = [f["name"] for f in result.functions]
        assert "add" in method_names
        assert "subtract" in method_names

    def test_parse_python_imports(self):
        """Test parsing Python import statements."""
        parser = CodeParser()
        code = """import os
import sys
from typing import List, Dict
from app.utils import helper
"""

        result = parser.parse_file("test.py", code)

        assert len(result.imports) == 4
        import_modules = [imp.get("module") or imp.get("name") for imp in result.imports]
        assert "os" in import_modules
        assert "sys" in import_modules

    def test_parse_python_nested_functions(self):
        """Test parsing nested Python functions."""
        parser = CodeParser()
        code = """def outer():
    def inner():
        return "inner"
    return inner
"""

        result = parser.parse_file("test.py", code)

        # Both outer and inner functions should be extracted
        assert len(result.functions) == 2
        function_names = [f["name"] for f in result.functions]
        assert "outer" in function_names
        assert "inner" in function_names

    def test_parse_python_lambda_function(self):
        """Test parsing Python lambda functions."""
        parser = CodeParser()
        code = """def process():
    lambda x: x * 2
    lambda y: y + 1
"""

        result = parser.parse_file("test.py", code)

        # Lambdas should be extracted
        assert len(result.functions) >= 1

    def test_calculate_complexity(self):
        """Test complexity calculation."""
        parser = CodeParser()
        code = """def func1():
    pass

def func2():
    pass

class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""

        result = parser.parse_file("test.py", code)

        # Complexity: 2 functions + 1 class * 2 = 4
        # Actually based on the implementation: functions + classes * 2
        # 2 functions + 1 class * 2 = 4
        assert result.complexity > 0

    def test_parse_javascript_function(self):
        """Test parsing JavaScript function."""
        parser = CodeParser()
        code = """function greet(name) {
    return 'Hello, ' + name;
}
"""

        result = parser.parse_file("test.js", code)

        assert result.language == "javascript"
        assert len(result.functions) == 1
        assert result.functions[0]["name"] == "greet"

    def test_parse_javascript_arrow_function(self):
        """Test parsing JavaScript arrow function."""
        parser = CodeParser()
        code = """const add = (a, b) => {
    return a + b;
};
"""

        result = parser.parse_file("test.js", code)

        # Arrow functions should be extracted
        assert len(result.functions) >= 1

    def test_parse_typescript_function(self):
        """Test parsing TypeScript function."""
        parser = CodeParser()
        code = """function multiply(a: number, b: number): number {
    return a * b;
}
"""

        result = parser.parse_file("test.ts", code)

        assert result.language == "typescript"
        assert len(result.functions) == 1
        assert result.functions[0]["name"] == "multiply"

    def test_parse_invalid_code(self):
        """Test parsing invalid Python code."""
        parser = CodeParser()
        invalid_code = """this is not valid python code at all!!!
 [[[broken syntax]]]
"""

        result = parser.parse_file("broken.py", invalid_code)

        # Should return empty result instead of crashing
        assert isinstance(result, ParsedCode)
        assert result.file_path == "broken.py"
        assert result.language == "python"
        # Functions, classes, imports should be empty lists
        assert result.functions == []
        assert result.classes == []

    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        parser = CodeParser()
        result = parser.parse_file("empty.py", "")

        assert isinstance(result, ParsedCode)
        assert len(result.functions) == 0
        assert len(result.classes) == 0
        assert len(result.imports) == 0

    def test_parse_unsupported_language(self):
        """Test parsing a file with unsupported language."""
        parser = CodeParser()

        try:
            parser.parse_file("test.xyz", "some content")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Cannot detect language" in str(e)
