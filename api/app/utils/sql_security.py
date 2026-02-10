"""
SQL security utilities.

Provides validation and safe construction of SQL queries to prevent injection attacks.
"""

import re
from typing import Collection


# Regex for valid SQL identifiers (PostgreSQL)
# Must start with letter or underscore, followed by letters, digits, underscores
_VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Regex for hex color format
_HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')

# Keywords that should not appear in a SELECT-only query
_DANGEROUS_SQL_KEYWORDS = frozenset([
    'DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE', 'ALTER', 'CREATE',
    'GRANT', 'REVOKE', 'EXECUTE', 'COPY', 'VACUUM', 'REINDEX', 'CLUSTER',
])

# SQL comment patterns to strip before validation
_SQL_COMMENT_PATTERNS = [
    re.compile(r'--[^\n]*'),  # Single line comments
    re.compile(r'/\*.*?\*/', re.DOTALL),  # Multi-line comments
]


class SQLSecurityError(ValueError):
    """Raised when SQL validation fails due to potential security issues."""
    pass


def is_valid_identifier(name: str) -> bool:
    """
    Check if a name is a valid SQL identifier.

    A valid identifier:
    - Starts with a letter (a-z, A-Z) or underscore
    - Contains only letters, digits, and underscores
    - Is not empty

    Args:
        name: The identifier to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) > 128:  # PostgreSQL max identifier length is 63, we're lenient
        return False
    return bool(_VALID_IDENTIFIER_PATTERN.match(name))


def validate_identifier(name: str, identifier_type: str = "identifier") -> str:
    """
    Validate that a name is a safe SQL identifier.

    Args:
        name: The identifier to validate
        identifier_type: Description for error messages (e.g., "column", "table")

    Returns:
        The validated identifier (unchanged)

    Raises:
        SQLSecurityError: If the identifier is invalid
    """
    if not is_valid_identifier(name):
        raise SQLSecurityError(
            f"Invalid {identifier_type} name: '{name}'. "
            f"Must start with a letter or underscore and contain only letters, digits, and underscores."
        )
    return name


def validate_identifier_in_allowlist(
    name: str,
    allowlist: Collection[str],
    identifier_type: str = "identifier",
) -> str:
    """
    Validate that an identifier exists in an allowlist.

    This is the primary defense against SQL injection - only identifiers
    that exist in the actual schema are allowed.

    Args:
        name: The identifier to validate
        allowlist: Collection of allowed identifiers (e.g., column names from schema)
        identifier_type: Description for error messages

    Returns:
        The validated identifier

    Raises:
        SQLSecurityError: If the identifier is not in the allowlist
    """
    if name not in allowlist:
        raise SQLSecurityError(
            f"Unknown {identifier_type}: '{name}'. "
            f"Valid options: {', '.join(sorted(allowlist)[:10])}"
            f"{'...' if len(allowlist) > 10 else ''}"
        )
    return name


def validate_column_names(
    columns: list[str],
    schema_columns: Collection[str],
) -> list[str]:
    """
    Validate that all column names exist in the schema.

    Args:
        columns: List of column names to validate
        schema_columns: Set of valid column names from schema

    Returns:
        The validated column list

    Raises:
        SQLSecurityError: If any column is not in the schema
    """
    for col in columns:
        validate_identifier_in_allowlist(col, schema_columns, "column")
    return columns


def quote_identifier(name: str) -> str:
    """
    Quote a SQL identifier to prevent injection.

    Uses double quotes (PostgreSQL standard) and escapes any embedded quotes.
    Note: Should still validate identifiers against schema before using this.

    Args:
        name: The identifier to quote

    Returns:
        The quoted identifier
    """
    # Escape any existing double quotes by doubling them
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _strip_comments(sql: str) -> str:
    """Strip SQL comments from a query."""
    result = sql
    for pattern in _SQL_COMMENT_PATTERNS:
        result = pattern.sub('', result)
    return result


def validate_sql_is_select_only(sql: str) -> str:
    """
    Validate that SQL is a SELECT statement only (no DDL/DML).

    This provides defense-in-depth for derived dataset queries.

    Args:
        sql: The SQL query to validate

    Returns:
        The validated SQL (unchanged)

    Raises:
        SQLSecurityError: If the SQL contains dangerous operations
    """
    # Strip comments to prevent hiding dangerous keywords
    clean_sql = _strip_comments(sql)

    # Normalize whitespace and convert to uppercase for checking
    normalized = ' '.join(clean_sql.upper().split())

    # Must start with SELECT (after stripping leading whitespace)
    stripped = normalized.strip()
    if not stripped.startswith('SELECT'):
        raise SQLSecurityError(
            "Transformation SQL must be a SELECT statement. "
            f"Found: {sql[:50]}{'...' if len(sql) > 50 else ''}"
        )

    # Check for dangerous keywords outside of string literals
    # This is a conservative check - we look for keywords as whole words
    for keyword in _DANGEROUS_SQL_KEYWORDS:
        # Use word boundary matching to avoid false positives like "UPDATED_AT" column
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, normalized):
            raise SQLSecurityError(
                f"Dangerous SQL keyword '{keyword}' not allowed in transformation. "
                "Only SELECT queries are permitted."
            )

    # Check for multiple statements (semicolon outside strings)
    # This is a simplified check - a proper SQL parser would be more robust
    # Split by semicolon and check if there's more than one non-empty statement
    parts = [p.strip() for p in clean_sql.split(';') if p.strip()]
    if len(parts) > 1:
        raise SQLSecurityError(
            "Multiple SQL statements not allowed. Only a single SELECT is permitted."
        )

    return sql


def validate_hex_color(color: str | None) -> str | None:
    """
    Validate that a color string is a valid hex color.

    Args:
        color: The color string to validate (format: #RRGGBB)

    Returns:
        The validated color (unchanged) or None if input was None

    Raises:
        SQLSecurityError: If the color format is invalid
    """
    if color is None:
        return None

    if not _HEX_COLOR_PATTERN.match(color):
        raise SQLSecurityError(
            f"Invalid color format: '{color}'. "
            "Must be a hex color in format #RRGGBB (e.g., #FF5733)."
        )
    return color


def sql_literal(value) -> str:
    """
    Convert a Python value to a SQL literal safely.

    Args:
        value: The value to convert

    Returns:
        SQL literal string

    Raises:
        TypeError: If the value type is not supported
    """
    if value is None:
        return "NULL"
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, float):
        # Handle special float values
        if value != value:  # NaN
            return "NULL"
        elif value == float('inf') or value == float('-inf'):
            raise TypeError("Infinity values cannot be converted to SQL literals")
        return str(value)
    elif isinstance(value, str):
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    else:
        raise TypeError(f"Unsupported type for SQL literal: {type(value).__name__}")
