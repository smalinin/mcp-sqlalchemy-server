---

# MCP Server ODBC via SQLAlchemy

A lightweight MCP (Model Context Protocol) server for ODBC built with **FastAPI**, **pyodbc**, and **SQLAlchemy**. This server is compatible with Virtuoso DBMS and other DBMS backends that implement a SQLAlchemy provider.


![mcp-client-and-servers|648x499](https://www.openlinksw.com/data/screenshots/mcp-architecture.png)

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
# Usage 
## Database Management System (DBMS) Connection URLs 
Here are the pyodbc URL examples for connecting to DBMS systems that have been tested using this mcp-server.

| Database      | URL Format                                    |
|---------------|-----------------------------------------------|
| Virtuoso DBMS | `virtuoso+pyodbc://user:password@ODBC_DSN`    |
| PostgreSQL    | `postgresql://user:password@localhost/dbname` |
| MySQL         | `mysql+pymysql://user:password@localhost/dbname` |
| SQLite        | `sqlite:///path/to/database.db`               |
Once connected, you can interact with your WhatsApp contacts through Claude, leveraging Claude's AI capabilities in your WhatsApp conversations.

## Tools Provided

|name|description|
|---|---|
|get_qualifiers|Retrieve and return a list of all database qualifier for the connected DBMS|
|get_schemas|Retrieve and return a list of all schema names from the connected database.|
|get_tables|Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format [{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}].|
|describe_table|Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable, autoincrement, primary key, and foreign keys|
|filter_table_names|Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format [{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}].|
|query_database|Execute a SQL query and return results in JSONL format.|
|execute_query|Execute a SQL query and return results in JSONL format.|
|execute_query_md|Execute a SQL query and return results in Markdown table format.|
|spasql_query|Execute a SPASQL query and return results.|
|sparql_query|Execute a SPARQL query and return results.|
|virtuoso_support_ai|Interact with the Virtuoso Support Assistant/Agent -- a Virtuoso-specific feature for interacting with LLMs|

---

## Troubleshooting

For easier troubleshooting:
1. Install the MCP Inspector:
   ```bash
   npm install -g @modelcontextprotocol/inspector
   ```

2. Start the inspector:
   ```bash
   npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-sqlalchemy-server run mcp-sqlalchemy-server
   ```

Access the provided URL to troubleshoot server interactions.

