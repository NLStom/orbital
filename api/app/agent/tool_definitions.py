"""
Tool definitions for LLM API in JSON Schema format.

Each tool has:
- name: Tool identifier
- description: What the tool does
- input_schema: JSON Schema for the tool's parameters
"""

# Schema tools - understand data structure
SCHEMA_TOOL_DEFINITIONS = [
    {
        "name": "get_schema",
        "description": "Get the schema of all available tables, including column names and types. Use this first to understand what data is available.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_stats",
        "description": "Get statistics for a specific table, including row counts, data types, and summary statistics for numeric/categorical columns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Name of the table to analyze"}
            },
            "required": ["table"],
        },
    },
]

# SQL tools - query and create derived tables
SQL_TOOL_DEFINITIONS = [
    {
        "name": "run_sql",
        "description": (
            "Execute a SQL query against the data. Use for:\n"
            "- SELECT queries to retrieve and filter data\n"
            "- CREATE TABLE <name> AS SELECT to save intermediate results\n"
            "- JOINs across source tables and previously created derived tables\n"
            "- Aggregations (GROUP BY, COUNT, SUM, AVG, etc.)\n\n"
            "Tables are referenced by name (e.g., SELECT * FROM vn WHERE c_rating > 800).\n"
            "Use PostgreSQL SQL syntax."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL statement to execute",
                }
            },
            "required": ["sql"],
        },
    }
]

# Visualization tools - create charts
CHART_TOOL_DEFINITIONS = [
    {
        "name": "create_chart",
        "description": "Create a chart visualization from table data. Supports bar, line, scatter, pie, and area charts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Name of the table to visualize"},
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "scatter", "pie", "area"],
                    "description": "Type of chart to create",
                },
                "x": {"type": "string", "description": "Column for x-axis"},
                "y": {
                    "type": "string",
                    "description": "Column for y-axis (or values for pie chart)",
                },
                "title": {"type": "string", "description": "Optional chart title"},
                "color": {"type": "string", "description": "Optional column for color grouping"},
                "limit": {
                    "type": "integer",
                    "description": "Fetch at most this many rows before capping to top_n (default: 100)",
                    "default": 100,
                },
                "x_label": {
                    "type": "string",
                    "description": "Human-readable label for the x-axis (auto-generated from column name if omitted)",
                },
                "y_label": {
                    "type": "string",
                    "description": "Human-readable label for the y-axis (auto-generated from column name if omitted)",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of categories/data points to keep (default: 10, capped at 20)",
                    "default": 10,
                },
                "group_other": {
                    "type": "boolean",
                    "description": "When more than top_n rows exist, roll the remainder into an 'Other' bucket (numeric y-only)",
                    "default": False,
                },
                "series": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names to plot as separate y-axis series (for wide-format data like actual + predicted). Overrides y for data.",
                },
                "reference_lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "axis": {"type": "string", "enum": ["x", "y"]},
                            "value": {"type": ["string", "number"]},
                            "label": {"type": "string"},
                        },
                        "required": ["axis", "value"],
                    },
                    "description": "Reference lines to draw on the chart (e.g., train/test split cutoff).",
                },
                "dashed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Series names that should render with dashed lines (e.g., predicted values).",
                },
            },
            "required": ["table", "chart_type", "x", "y"],
        },
    }
]

# Interaction tools - communicate with the user mid-loop
INTERACTION_TOOL_DEFINITIONS = [
    {
        "name": "ask_user",
        "description": "Ask the user a clarifying question before continuing. Use this when the request is vague or ambiguous and you need more information to proceed effectively.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The clarifying question to ask the user",
                }
            },
            "required": ["question"],
        },
    }
]

# ML model training tools
TRAIN_MODEL_TOOL_DEFINITIONS = [
    {
        "name": "train_model",
        "description": (
            "Train a supervised ML model (regression or classification) on a table. "
            "Automatically detects model type from the target column, selects features, "
            "trains a model, and saves predictions + residuals as a new table for analysis.\n\n"
            "Use when you want to:\n"
            "- Predict a numeric or categorical target from other columns\n"
            "- Measure how well available features explain a target (R2, accuracy)\n"
            "- Identify which features matter most (feature importances)\n"
            "- Analyze prediction errors (residuals) to discover missing patterns"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Name of the table containing the training data",
                },
                "target": {
                    "type": "string",
                    "description": "Column to predict",
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Feature columns to use. If omitted, auto-detects all numeric "
                        "columns and one-hot encodes low-cardinality categoricals."
                    ),
                },
                "model_type": {
                    "type": "string",
                    "enum": ["auto", "regression", "classification"],
                    "description": (
                        "Model type. 'auto' detects from target: string/bool/few-unique → "
                        "classification, otherwise regression."
                    ),
                    "default": "auto",
                },
                "algorithm": {
                    "type": "string",
                    "enum": ["random_forest", "gradient_boosting", "linear"],
                    "description": "ML algorithm to use (default: random_forest)",
                    "default": "random_forest",
                },
                "test_size": {
                    "type": "number",
                    "description": "Fraction of data for test set (default: 0.2)",
                    "default": 0.2,
                },
                "random_state": {
                    "type": "integer",
                    "description": "Random seed for reproducibility (default: 42)",
                    "default": 42,
                },
                "split_by": {
                    "type": "string",
                    "description": (
                        "Column name for temporal/ordered train-test split. "
                        "When set, data is sorted by this column and split chronologically "
                        "(first rows = train, last rows = test) instead of randomly. "
                        "Use for time-series data to prevent data leakage. "
                        "Column must be numeric or datetime."
                    ),
                },
            },
            "required": ["table", "target"],
        },
    }
]

# Memory tools - session-scoped agent memory
MEMORY_TOOL_DEFINITIONS = [
    {
        "name": "update_memory",
        "description": (
            "Store important facts, user preferences, or analysis conclusions in session memory. "
            "Call this when you discover something worth remembering for later turns. "
            "Memory persists for the entire session and is shown to you at the start of each turn.\n\n"
            "When to use:\n"
            "- After discovering a key insight (revenue numbers, patterns, etc.)\n"
            "- When user corrects you or states a preference\n"
            "- After completing a significant analysis\n"
            "- To remove outdated information\n\n"
            "Keep memories concise - store the insight, not the raw data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove"],
                    "description": "Add new memory or remove outdated one",
                },
                "category": {
                    "type": "string",
                    "enum": ["fact", "preference", "correction", "conclusion"],
                    "description": "Type of memory: fact (data observed), preference (user style), correction (user clarification), conclusion (analysis insight)",
                },
                "content": {
                    "type": "string",
                    "description": "The thing to remember (be concise)",
                },
            },
            "required": ["action", "category", "content"],
        },
    }
]

# Report tools - create shareable reports
REPORT_TOOL_DEFINITIONS = [
    {
        "name": "create_report",
        "description": (
            "Create a shareable report summarizing analysis findings. "
            "Use after completing an analysis to give the user a clean, "
            "shareable summary. Include narrative text explaining what "
            "was found and embed key charts. Keep to 3-6 sections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Report title (e.g., 'Home Price Prediction Analysis')",
                },
                "sections": {
                    "type": "array",
                    "description": (
                        "Ordered list of report sections (max 8). "
                        "Each section is either narrative text or an embedded chart."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["text", "chart"],
                                "description": "'text' for narrative paragraphs, 'chart' for embedded visualizations",
                            },
                            "content": {
                                "type": "string",
                                "description": "Markdown text (for text sections)",
                            },
                            "title": {
                                "type": "string",
                                "description": "Chart title (for chart sections)",
                            },
                            "table": {
                                "type": "string",
                                "description": "Table name to pull chart data from (for chart sections)",
                            },
                            "chart_type": {
                                "type": "string",
                                "enum": ["bar", "line", "scatter", "pie", "area"],
                                "description": "Chart type (for chart sections)",
                            },
                            "x": {"type": "string", "description": "Column for x-axis"},
                            "y": {"type": "string", "description": "Column for y-axis"},
                            "color": {"type": "string", "description": "Optional column for color grouping"},
                        },
                        "required": ["type"],
                    },
                },
            },
            "required": ["title", "sections"],
        },
    }
]

# Combine all tool definitions
ALL_TOOL_DEFINITIONS = (
    SCHEMA_TOOL_DEFINITIONS
    + SQL_TOOL_DEFINITIONS
    + TRAIN_MODEL_TOOL_DEFINITIONS
    + CHART_TOOL_DEFINITIONS
    + INTERACTION_TOOL_DEFINITIONS
    + MEMORY_TOOL_DEFINITIONS
    + REPORT_TOOL_DEFINITIONS
)
