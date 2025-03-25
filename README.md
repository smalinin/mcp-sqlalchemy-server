---

# MCP Server ODBC via SQLAlchemy

A lightweight MCP (Model Context Protocol) server for ODBC built with **FastAPI**, **pyodbc**, and **SQLAlchemy**. This server is compatible with Virtuoso DBMS and other DBMS backends that implement a SQLAlchemy provider.

---

## Features

- **Get Schemas**: Fetch and list all schema names from the connected database.
- **Get Tables**: Retrieve table information for specific schemas or all schemas.
- **Describe Table**: Generate a detailed description of table structures, including:
  - Column names and data types
  - Nullable attributes
  - Primary and foreign keys
- **Search Tables**: Filter and retrieve tables based on name substrings.
- **Execute Stored Procedures**: In the case of Virtuoso, execute stored procedures and retrieve results.
- **Execute Queries**:
  - JSONL result format: Optimized for structured responses.
  - Markdown table format: Ideal for reporting and visualization.

---

## Prerequisites

1. **Install uv**:
   ```bash
   pip install uv
   ```
   Or use Homebrew:
   ```bash
   brew install uv
   ```

2. **ODBC DSN Setup**: Configure your ODBC Data Source Name (`~/.odbc.ini`) for the target database. Example for Virtuoso DBMS:
   ```
   [VOS]
   Description = OpenLink Virtuoso
   Driver = /path/to/virtodbcu_r.so
   Database = Demo
   Address = localhost:1111
   WideAsUTF16 = Yes
   ```

3. **SQLAlchemy URL Binding**: Use the format:
   ```
   virtuoso+pyodbc://user:password@VOS
   ```

---

## Installation

Clone this repository:
```bash
git clone https://github.com/OpenLinkSoftware/mcp-sqlalchemy-server.git
```

---

## Configuration

For **Claude Desktop** users:
Add the following to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "my_database": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-sqlalchemy-server", "run", "mcp-sqlalchemy-server"],
      "env": {
        "DB_URL": "virtuoso+pyodbc://user:password@VOS"
      }
    }
  }
}
```

---

## Examples of Database URL Configuration

| Database      | URL Format                                    |
|---------------|-----------------------------------------------|
| Virtuoso DBMS | `virtuoso+pyodbc://user:password@ODBC_DSN`    |
| PostgreSQL    | `postgresql://user:password@localhost/dbname` |
| MySQL         | `mysql+pymysql://user:password@localhost/dbname` |
| SQLite        | `sqlite:///path/to/database.db`               |

---

## Debugging

For easier debugging:
1. Install the MCP Inspector:
   ```bash
   npm install -g @modelcontextprotocol/inspector
   ```

2. Start the inspector:
   ```bash
   npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-sqlalchemy-server run mcp-sqlalchemy-server
   ```

Access the provided URL to troubleshoot server interactions.

