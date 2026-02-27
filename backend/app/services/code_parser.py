import ast
import logging
from dataclasses import dataclass

from app.models.pr_models import PRFile

logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    entity_type: str  # function, class, loop, try_except, import, etc.
    name: str  # Name of the entity (if applicable)
    line_start: int  # Starting line number (1-indexed)
    line_end: int  # Ending line number (1-indexed)
    complexity: int | None = None  # Cyclomatic complexity (for functions)
    decorators: list[str] | None = None  # Decorator names
    docstring: str | None = None  # Docstring content
    parent: str | None = None  # Parent class or function (for nested entities)


@dataclass
class ParsedFile:
    filename: str
    entities: list[CodeEntity]
    raw_content: str
    total_lines: int
    imports: list[str]
    has_main_guard: bool
    syntax_errors: list[str]


class ASTVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]):
        self.entities: list[CodeEntity] = []
        self.imports: list[str] = []
        self.source_lines = source_lines
        self.has_main_guard = False
        self.current_parent: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:

        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Get docstring
        docstring = ast.get_docstring(node)

        # Calculate basic complexity (count branches)
        complexity = self._calculate_complexity(node)

        entity = CodeEntity(
            entity_type="function",
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            complexity=complexity,
            decorators=decorators if decorators else None,
            docstring=docstring,
            parent=self.current_parent,
        )

        self.entities.append(entity)

        # Visit nested functions
        previous_parent = self.current_parent
        self.current_parent = node.name
        self.generic_visit(node)
        self.current_parent = previous_parent

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:

        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        complexity = self._calculate_complexity(node)

        entity = CodeEntity(
            entity_type="async_function",
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            complexity=complexity,
            decorators=decorators if decorators else None,
            docstring=docstring,
            parent=self.current_parent,
        )

        self.entities.append(entity)

        previous_parent = self.current_parent
        self.current_parent = node.name
        self.generic_visit(node)
        self.current_parent = previous_parent

    def visit_ClassDef(self, node: ast.ClassDef) -> None:

        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        entity = CodeEntity(
            entity_type="class",
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=decorators if decorators else None,
            docstring=docstring,
            parent=self.current_parent,
        )

        self.entities.append(entity)

        # Visit methods inside class
        previous_parent = self.current_parent
        self.current_parent = node.name
        self.generic_visit(node)
        self.current_parent = previous_parent

    def visit_For(self, node: ast.For) -> None:

        entity = CodeEntity(
            entity_type="for_loop",
            name=f"loop_{node.lineno}",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parent=self.current_parent,
        )
        self.entities.append(entity)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:

        entity = CodeEntity(
            entity_type="while_loop",
            name=f"while_{node.lineno}",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parent=self.current_parent,
        )
        self.entities.append(entity)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:

        entity = CodeEntity(
            entity_type="try_except",
            name=f"try_{node.lineno}",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parent=self.current_parent,
        )
        self.entities.append(entity)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:

        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:

        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:

        if self._is_main_guard(node):
            self.has_main_guard = True
        self.generic_visit(node)

    def _get_decorator_name(self, decorator: ast.expr) -> str:

        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return "unknown"

    def _calculate_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> int:

        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _is_main_guard(self, node: ast.If) -> bool:

        if not isinstance(node.test, ast.Compare):
            return False

        test = node.test
        if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
            return False

        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            return False

        if len(test.comparators) != 1:
            return False

        comparator = test.comparators[0]
        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
            return True

        return False


def parse_python_file(filename: str, content: str) -> ParsedFile:

    syntax_errors = []

    try:
        tree = ast.parse(content, filename=filename)
        source_lines = content.splitlines()

        visitor = ASTVisitor(source_lines)
        visitor.visit(tree)

        parsed = ParsedFile(
            filename=filename,
            entities=visitor.entities,
            raw_content=content,
            total_lines=len(source_lines),
            imports=visitor.imports,
            has_main_guard=visitor.has_main_guard,
            syntax_errors=syntax_errors,
        )

        logger.info(
            "Parsed file | filename=%s | entities=%s | lines=%s",
            filename,
            len(parsed.entities),
            parsed.total_lines,
        )

        return parsed

    except SyntaxError as e:
        error_msg = f"Line {e.lineno}: {e.msg}"
        syntax_errors.append(error_msg)

        logger.warning(
            "Syntax error in file | filename=%s | error=%s", filename, error_msg
        )

        # Return partial result with error
        return ParsedFile(
            filename=filename,
            entities=[],
            raw_content=content,
            total_lines=len(content.splitlines()),
            imports=[],
            has_main_guard=False,
            syntax_errors=syntax_errors,
        )


def parse(files: list[PRFile]) -> list[ParsedFile]:

    parsed_files = []

    for pr_file in files:
        # Skip files without patches (deleted files)
        if not pr_file.patch and not pr_file.content:
            logger.debug(
                "Skipping file without content | filename=%s", pr_file.filename
            )
            continue

        # Use patch or content
        content = pr_file.content if pr_file.content else pr_file.patch or ""

        try:
            parsed = parse_python_file(pr_file.filename, content)
            parsed_files.append(parsed)

        except Exception as e:
            logger.error(
                "Failed to parse file | filename=%s | error=%s",
                pr_file.filename,
                str(e),
            )
            # Continue processing other files

    logger.info(
        "Completed parsing | total_files=%s | successfully_parsed=%s",
        len(files),
        len(parsed_files),
    )

    return parsed_files
