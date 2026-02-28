import pytest

from app.models.pr_models import PRFile
from app.services import code_parser


class TestParseSimpleFunction:
    def test_parses_function_with_name_and_lines(self):
        """Should extract function name and line numbers."""
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        parsed = code_parser.parse_python_file("test.py", code)

        assert len(parsed.entities) == 1
        entity = parsed.entities[0]
        assert entity.entity_type == "function"
        assert entity.name == "hello_world"
        assert entity.line_start == 2
        assert entity.line_end == 4

    def test_parses_function_with_docstring(self):
        code = '''
def greet(name):
    """Greet a person by name."""
    return f"Hello, {name}"
'''
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.docstring == "Greet a person by name."

    def test_parses_function_with_decorators(self):
        code = """
@staticmethod
@cache
def compute():
    return 42
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.decorators == ["staticmethod", "cache"]


class TestParseAsyncFunction:
    def test_identifies_async_function(self):
        code = """
async def fetch_data():
    await something()
    return data
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.entity_type == "async_function"
        assert entity.name == "fetch_data"


class TestParseClass:
    def test_parses_class_with_methods(self):
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
"""
        parsed = code_parser.parse_python_file("test.py", code)

        # Should have 1 class and 2 methods
        assert len(parsed.entities) == 3

        class_entity = parsed.entities[0]
        assert class_entity.entity_type == "class"
        assert class_entity.name == "Calculator"

        method1 = parsed.entities[1]
        assert method1.entity_type == "function"
        assert method1.name == "add"
        assert method1.parent == "Calculator"

        method2 = parsed.entities[2]
        assert method2.entity_type == "function"
        assert method2.name == "subtract"
        assert method2.parent == "Calculator"

    def test_parses_class_with_docstring(self):
        code = '''
class DataProcessor:
    """Process data efficiently."""
    pass
'''
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.docstring == "Process data efficiently."


class TestParseLoops:
    def test_parses_for_loop(self):
        code = """
for i in range(10):
    print(i)
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.entity_type == "for_loop"
        assert entity.line_start == 2

    def test_parses_while_loop(self):
        code = """
while True:
    process()
    break
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.entity_type == "while_loop"


class TestParseTryExcept:
    def test_parses_try_except_block(self):
        code = """
try:
    risky_operation()
except Exception as e:
    handle_error(e)
finally:
    cleanup()
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.entity_type == "try_except"
        assert entity.line_start == 2


class TestParseImports:
    def test_captures_import_statements(self):
        code = """
import os
import sys
from pathlib import Path
from collections import defaultdict
"""
        parsed = code_parser.parse_python_file("test.py", code)

        assert "os" in parsed.imports
        assert "sys" in parsed.imports
        assert "pathlib" in parsed.imports
        assert "collections" in parsed.imports


class TestComplexityCalculation:
    def test_simple_function_has_complexity_1(self):
        code = """
def simple():
    return 42
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.complexity == 1

    def test_function_with_if_increases_complexity(self):
        code = """
def check(x):
    if x > 0:
        return "positive"
    return "non-positive"
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        assert entity.complexity == 2

    def test_function_with_multiple_branches(self):
        code = """
def process(data):
    if data is None:
        return None
    
    for item in data:
        if item > 0:
            yield item
    
    while True:
        if condition():
            break
"""
        parsed = code_parser.parse_python_file("test.py", code)

        entity = parsed.entities[0]
        # if, for, if, while, if = 5 branches + 1 base = 6
        assert entity.complexity >= 5


class TestMainGuardDetection:
    def test_detects_main_guard(self):
        code = """
def main():
    print("Running")

if __name__ == "__main__":
    main()
"""
        parsed = code_parser.parse_python_file("test.py", code)

        assert parsed.has_main_guard is True

    def test_detects_absence_of_main_guard(self):
        code = """
def main():
    print("Running")

main()
"""
        parsed = code_parser.parse_python_file("test.py", code)

        assert parsed.has_main_guard is False


class TestSyntaxErrorHandling:
    def test_captures_syntax_error(self):
        code = """
def broken(
    # Missing closing parenthesis
    print("This won't parse")
"""
        parsed = code_parser.parse_python_file("test.py", code)

        assert len(parsed.syntax_errors) > 0
        assert parsed.entities == []

    def test_returns_partial_results_on_error(self):
        code = "def broken("

        parsed = code_parser.parse_python_file("test.py", code)

        assert parsed.filename == "test.py"
        assert parsed.total_lines > 0
        assert len(parsed.syntax_errors) > 0


class TestNestedStructures:
    def test_parses_nested_functions(self):
        code = """
def outer():
    def inner():
        return 1
    return inner()
"""
        parsed = code_parser.parse_python_file("test.py", code)

        outer = parsed.entities[0]
        inner = parsed.entities[1]

        assert outer.name == "outer"
        assert outer.parent is None

        assert inner.name == "inner"
        assert inner.parent == "outer"

    def test_parses_nested_classes(self):
        code = """
class Outer:
    class Inner:
        def method(self):
            pass
"""
        parsed = code_parser.parse_python_file("test.py", code)

        outer_class = [e for e in parsed.entities if e.name == "Outer"][0]
        inner_class = [e for e in parsed.entities if e.name == "Inner"][0]
        method = [e for e in parsed.entities if e.name == "method"][0]

        assert inner_class.parent == "Outer"
        assert method.parent == "Inner"


class TestParseMultipleFiles:
    def test_parses_multiple_files(self):
        file1 = PRFile(
            filename="script1.py",
            status="modified",
            additions=10,
            deletions=2,
            changes=12,
            patch="def hello(): pass",
            sha="abc123",
        )

        file2 = PRFile(
            filename="script2.py",
            status="added",
            additions=20,
            deletions=0,
            changes=20,
            patch="class Test: pass",
            sha="def456",
        )

        result = code_parser.parse([file1, file2])

        assert len(result) == 2
        assert result[0].filename == "script1.py"
        assert result[1].filename == "script2.py"

    def test_skips_files_without_content(self):
        file_with_content = PRFile(
            filename="script.py",
            status="modified",
            additions=5,
            deletions=1,
            changes=6,
            patch="def test(): pass",
            sha="abc123",
        )

        file_without_content = PRFile(
            filename="deleted.py",
            status="removed",
            additions=0,
            deletions=50,
            changes=50,
            patch=None,
            content=None,
            sha="xyz789",
        )

        result = code_parser.parse([file_with_content, file_without_content])

        assert len(result) == 1
        assert result[0].filename == "script.py"

    def test_continues_on_parse_error(self):
        good_file = PRFile(
            filename="good.py",
            status="modified",
            additions=5,
            deletions=0,
            changes=5,
            patch="def valid(): pass",
            sha="abc123",
        )

        bad_file = PRFile(
            filename="bad.py",
            status="modified",
            additions=5,
            deletions=0,
            changes=5,
            patch="def broken(",
            sha="def456",
        )

        result = code_parser.parse([good_file, bad_file])

        # Should still parse the good file
        good_parsed = [f for f in result if f.filename == "good.py"]
        assert len(good_parsed) == 1


class TestRealWorldExamples:
    def test_parses_fastapi_route(self):
        code = '''
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Fetch user by ID."""
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(404)
    return user
'''
        parsed = code_parser.parse_python_file("routes.py", code)

        entity = parsed.entities[0]
        assert entity.entity_type == "async_function"
        assert entity.name == "get_user"
        assert len(entity.decorators) >= 1

    def test_parses_dataclass(self):
        code = '''
from dataclasses import dataclass

@dataclass
class User:
    """User model."""
    id: int
    name: str
    email: str
'''
        parsed = code_parser.parse_python_file("models.py", code)

        class_entity = [e for e in parsed.entities if e.entity_type == "class"][0]
        assert class_entity.name == "User"
        assert "dataclass" in class_entity.decorators
