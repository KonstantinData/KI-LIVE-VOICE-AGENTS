"""
Governance Agent — Code Scanner
==================================
What:    AST-based and regex-based scanner for Python and TypeScript source files.
Does:    Parses source files and exposes helper methods for pattern detection used by rule modules.
Why:     Centralises all file I/O and parsing so rules stay pure logic without file handling.
Who:     All rules modules (dsgvo.py, security.py, multi_tenant.py, eu_ai_act.py, documentation.py).
Depends: ast (stdlib), re (stdlib), pathlib, src.agents.governance.config
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from src.agents.governance.config import GovernanceConfig


class FileScanner:
    """
    Provides file discovery and content analysis utilities for the governance agent.

    Combines AST parsing (Python) and regex patterns (Python + TypeScript)
    to detect compliance-relevant patterns without executing any code.
    """

    def __init__(self, config: GovernanceConfig) -> None:
        self._config = config
        self._root = config.repo_root

    # ──────────────────────────────────────────────────────────────────────
    # File Discovery
    # ──────────────────────────────────────────────────────────────────────

    def find_python_files(self) -> list[Path]:
        """Return all Python source files under the configured scan paths."""
        files: list[Path] = []
        for rel_path in self._config.scan_python_paths:
            base = self._root / rel_path
            if not base.exists():
                continue
            for f in base.rglob("*.py"):
                if not self._is_excluded(f):
                    files.append(f)
        return sorted(files)

    def find_ts_files(self) -> list[Path]:
        """Return all TypeScript/JavaScript source files under the configured scan paths."""
        files: list[Path] = []
        for rel_path in self._config.scan_ts_paths:
            base = self._root / rel_path
            if not base.exists():
                continue
            for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx"):
                for f in base.rglob(pattern):
                    if not self._is_excluded(f):
                        files.append(f)
        return sorted(files)

    def find_all_source_files(self) -> list[Path]:
        """Return all Python + TypeScript source files."""
        return self.find_python_files() + self.find_ts_files()

    def _is_excluded(self, path: Path) -> bool:
        """Return True if any path component matches the exclude list."""
        return any(part in self._config.exclude_dirs for part in path.parts)

    # ──────────────────────────────────────────────────────────────────────
    # Content Helpers
    # ──────────────────────────────────────────────────────────────────────

    def read_file(self, path: Path) -> str | None:
        """
        Read file content safely.

        Returns:
            File content as string, or None if the file cannot be read.
        """
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

    def grep(self, path: Path, pattern: str, flags: int = 0) -> list[tuple[int, str]]:
        """
        Search a file for a regex pattern, line by line.

        Args:
            path: File to search.
            pattern: Regex pattern string.
            flags: re module flags (e.g. re.IGNORECASE).

        Returns:
            List of (line_number, line_content) tuples for matching lines.
        """
        content = self.read_file(path)
        if content is None:
            return []
        matches: list[tuple[int, str]] = []
        compiled = re.compile(pattern, flags)
        for lineno, line in enumerate(content.splitlines(), start=1):
            if compiled.search(line):
                matches.append((lineno, line.rstrip()))
        return matches

    def grep_all(
        self, pattern: str, file_type: str = "python", flags: int = 0
    ) -> list[tuple[Path, int, str]]:
        """
        Search all files of a given type for a pattern.

        Args:
            pattern: Regex pattern.
            file_type: "python", "ts", or "all".
            flags: re module flags.

        Returns:
            List of (path, line_number, line_content) tuples.
        """
        if file_type == "python":
            files = self.find_python_files()
        elif file_type == "ts":
            files = self.find_ts_files()
        else:
            files = self.find_all_source_files()

        results: list[tuple[Path, int, str]] = []
        for f in files:
            for lineno, line in self.grep(f, pattern, flags):
                results.append((f, lineno, line))
        return results

    def file_contains(self, path: Path, pattern: str, flags: int = 0) -> bool:
        """Return True if the file contains at least one match for the pattern."""
        return len(self.grep(path, pattern, flags)) > 0

    def rel(self, path: Path) -> str:
        """Return path relative to repo root as a forward-slash string."""
        try:
            return str(path.relative_to(self._root)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    # ──────────────────────────────────────────────────────────────────────
    # Python AST Helpers
    # ──────────────────────────────────────────────────────────────────────

    def parse_python_ast(self, path: Path) -> ast.Module | None:
        """
        Parse a Python file into an AST.

        Returns:
            Parsed AST module, or None on syntax error.
        """
        content = self.read_file(path)
        if content is None:
            return None
        try:
            return ast.parse(content, filename=str(path))
        except SyntaxError:
            return None

    def get_function_names(self, path: Path) -> list[str]:
        """Return all top-level and class-level function names in a Python file."""
        tree = self.parse_python_ast(path)
        if tree is None:
            return []
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.append(node.name)
        return names

    def has_decorator(self, path: Path, decorator_name: str) -> list[tuple[int, str]]:
        """
        Find all functions/methods decorated with the given decorator name.

        Returns:
            List of (line_number, function_name) tuples.
        """
        tree = self.parse_python_ast(path)
        if tree is None:
            return []
        results: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call):
                        func = dec.func
                        if isinstance(func, ast.Name):
                            dec_name = func.id
                        elif isinstance(func, ast.Attribute):
                            dec_name = func.attr
                    if decorator_name in dec_name:
                        results.append((node.lineno, node.name))
        return results

    # ──────────────────────────────────────────────────────────────────────
    # Document Existence Checks
    # ──────────────────────────────────────────────────────────────────────

    def document_exists(self, rel_path: str) -> bool:
        """Return True if the document exists and is non-empty."""
        full_path = self._root / rel_path
        if not full_path.exists():
            return False
        return full_path.stat().st_size > 100  # must have real content, not just placeholder
