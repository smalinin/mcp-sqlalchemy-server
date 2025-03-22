# mcp-server-odbc 

A simple MCP ODBC server using FastAPI, ODBC and SQLAlchemy.
Tested with Virtuoso DBMS and coudl work with any SQLAlchemy-compatible databases.
  
## Components

The server implements next tools:

-  **get_schemas**
	- Retrieve and return a list of all schema names from the connected database.

-  **get_tables(schema: Optional[str] = None)**
	- Retrieve and return a list containing information about tables in the format
   `[{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table':'table_name'}]`
      Args:
      `schema (Optional[str])`: The name of the schema to retrieve tables for. If None, retrieves tables for all schemas.

- **describe_table(schema:str, table: str)**
	- Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable,  autoincrement, primary key, and foreign keys.
	- Args:
	`schema (Optional[str])`: The name of the schema to retrieve the table definition for. If None, retrieves the table definition for all schemas.
	`table (str)`: The name of the table to retrieve the definition for.

- **filter_table_names(q: str)**
	- Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format :
`[{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}]`
	- Args:
	`q (str)`: The substring to filter table names by.

- **execute_query(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None)**
	- Execute a SQL query and return results in JSONL format.
	- Args:
		`query (str)`  The SQL query to execute.
		`max_rows (int)` Maximum number of rows to return. Default is 100.
		`params (Optional[Dict[str, Any]])`  Optional dictionary of parameters to pass to the query.

- **execute_query_md(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None)**
	- Execute a SQL query and return results in Markdown table format.
	- Args:
		`query (str)`  The SQL query to execute.
		`max_rows (int)` Maximum number of rows to return. Default is 100.
		`params (Optional[Dict[str, Any]])`  Optional dictionary of parameters to pass to the query.

## Prerequisites

 - `uv` installed, you can install it using `pip install uv` or `brew install uv`

- Create an ODBC DSN (Data Source Name) that points to your target Virtuoso multi-model DBMS instance via `~/.odbc.ini`, as in the following sample:

```ini
; Data Source Name and associated Driver Section
; usually titled [ODBC Data Sources]
VOS          = OpenLink Virtuoso ODBC Driver (Unicode)

; Data Source Name and associated Driver Library section
[VOS]
Description = Open Virtuoso
Driver      = /usr/local/virtuoso-opensource/lib/virtodbcu_r.so
Database    = Demo
Address     = localhost:1111
WideAsUTF16 = Yes
```
**NOTE:** 
`WideAsUTF16 = Yes` is a mandatory attribute. It is used to transform Unicode methods and data in Virtuoso ODBC to the UTF16 character set, as is required by the `unixODBC` Driver Manager. 

Most parameters depend on your installation, but be sure to use `virtodbcu_r.so` which comprises [OpenLink Virtuoso ](https://virtuoso.openlinksw.com) 7.2 ODBC driver or Virtuoso 8.x ODBC driver functionality.

Via SQLAlchemy, DSN binding occurs via a `virtuoso+pyodbc` scheme URI. 
```python
"virtuoso+pyodbc://user:password@VOS"
```


## Installation

1. Clone repository:
```bash
git clone https://github.com/OpenLinkSoftware/mcp-server-odbc.git
```
2. Add database to claude_desktop_config.json (see below)


## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

   - On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my_database": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-server-odbc", "run", "mcp-server-odbc"],
      "env": {
        "DB_URL": "virtuoso+pyodbc://demo:demo@VOS",
      }
    }
  }
}
```

Environment Variables:

- `DB_URL`: SQLAlchemy [database URL](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls) (required)
  Examples:
  - Virtuoso DBMS: `virtuoso+pyodbc://user:password@your_ODBC_DSN`
  - PostgreSQL: `postgresql://user:password@localhost/dbname`
  - MySQL: `mysql+pymysql://user:password@localhost/dbname`
  - MariaDB: `mariadb+pymysql://user:password@localhost/dbname`
  - SQLite: `sqlite:///path/to/database.db`
  
- `MAX_LONG_DATA`: Maximum output length for LONG VARCHAR data (optional, default 4096)



## Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).
You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

**stdio**
- create file `/path/to/mcp-server-odbc/.env`  with next content
```
DB_URL="virtuoso+pyodbc://demo:demo@VOS" 
```
- run
```bash
npx  @modelcontextprotocol/inspector  uv  --directory /path/to/mcp-server-odbc  run  mcp-server-odbc
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

**SSE**
```bash
# Start MCP-odbc-server with SSE transport
DB_URL="virtuoso+pyodbc://demo:demo@VOS" FASTMCP_PORT=8000 uv run mcp-server-odbc --transport sse

# Start the MCP Inspector in another terminal
npx  @modelcontextprotocol/inspector
```

