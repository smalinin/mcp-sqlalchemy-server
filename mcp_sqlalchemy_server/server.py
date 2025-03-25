from datetime import datetime, date
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Any, Dict, List, Optional
import json

from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Retrieve database connection details from environment variables
DB_URL = os.getenv("DB_URL")
MAX_LONG_DATA = int(os.getenv("MAX_LONG_DATA",4096))

### Database ###

def get_engine(readonly=True):
    connection_string = os.getenv('DB_URL')
    if not connection_string:
        logging.error("DB_URL environment variable is not set.")
        raise ValueError("DB_URL environment variable is not set.")
    # connection_string = "virtuoso+pyodbc://dba:dba@VOS"
    return create_engine(connection_string, isolation_level='AUTOCOMMIT', execution_options={'readonly': readonly})

def get_db_info():
    try:
        engine = get_engine(readonly=True)
        with engine.connect() as conn:
            url = engine.url
            return (f"Connected to [{engine.dialect.name}] "
                    f"version {'.'.join(str(x) for x in engine.dialect.server_version_info)} "
                    f"DSN '{url.host}' "
                    f"as user '{url.username}'")
    except SQLAlchemyError as e:
        logging.error(f"Error connecting to the database: {e}")
        raise

### Constants ###
#DB_INFO = get_db_info()


### MCP ###
mcp = FastMCP('mcp-sqlalchemy-server', transport=["stdio", "sse"])

@mcp.tool(
    name="get_schemas",
    description="Retrieve and return a list of all schema names from the connected database."
)
def get_schemas() -> str:
    """
    Retrieve and return a list of all schema names from the connected database.

    Returns:
        str: A list of schema names.
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)

        schemas = inspector.get_schema_names()
        # return schemas
        return json.dumps(schemas)

    except SQLAlchemyError as e:
        logging.error(f"Error retrieving schemas: {e}")
        raise


@mcp.tool(
    name="get_tables",
    description="Retrieve and return a list containing information about tables in the format "
                "[{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}]. "
                "If `schema` is None, returns tables for all schemas. "
                "If `schema` is not None, returns tables for the specified schema."
)
def get_tables(Schema: Optional[str] = None) -> str:
    """
    Retrieve and return a list containing information about tables in the format
    [{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}].

    If `schema` is None, returns tables for all schemas.
    If `schema` is not None, returns tables for the specified schema.

    Args:
        schema (Optional[str]): The name of the schema to retrieve tables for. If None, retrieves tables for all schemas.

    Returns:
        str: A list containing information about tables in the specified format.
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)

        tables_info = []

        if Schema is None:
            # Retrieve a list of all schema names
            schemas = inspector.get_schema_names()

            # Iterate over each schema to retrieve table names
            for schema_name in schemas:
                tables = inspector.get_table_names(schema=schema_name)
                for table in tables:
                    tables_info.append({"schema": schema_name, "table": table})
        else:
            # Retrieve table names for the specified schema
            tables = inspector.get_table_names(schema=Schema)
            for table in tables:
                tables_info.append({"schema": Schema, "table": table})

        # Return the list containing table information
        # return tables_info
        return json.dumps(tables_info)
    
    except SQLAlchemyError as e:
        logging.error(f"Error retrieving tables: {e}")
        raise
        

@mcp.tool(
    name="describe_table",
    description="Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable,"
                " autoincrement, primary key, and foreign keys."
)
def describe_table(Schema:str, table: str) -> str:
    """
    Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable, autoincrement, primary key, and foreign keys.

    If `schema` is None, returns the table definition for the specified table in all schemas.
    If `schema` is not None, returns the table definition for the specified table in the specified schema.

    Args:
        schema (Optional[str]): The name of the schema to retrieve the table definition for. If None, retrieves the table definition for all schemas.
        table (str): The name of the table to retrieve the definition for.

    Returns:
        str: A dictionary containing the table definition, including column names, data types, nullable, autoincrement, primary key, and foreign keys.
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)

        table_definition = {}

        if inspector.has_table(table_name=table, schema=Schema):
                table_definition = _get_table_info(inspector, Schema, table)

        # return table_definition
        return json.dumps(table_definition)
    except SQLAlchemyError as e:
        logging.error(f"Error retrieving table definition: {e}")
        raise


def _get_table_info(inspector, Schema: str, table: str) -> Dict[str, Any]:
    """
    Helper function to retrieve table information including columns and constraints.

    Args:
        inspector: SQLAlchemy inspector object.
        schema (str): The name of the schema.
        table (str): The name of the table.

    Returns:
        Dict[str, Any]: A dictionary containing the table definition, including column names, data types, nullable, autoincrement, primary key, and foreign keys.
    """
    try:
        columns = inspector.get_columns(table, schema=Schema)
        primary_keys = inspector.get_pk_constraint(table, schema=Schema)['constrained_columns']
        foreign_keys = inspector.get_foreign_keys(table, schema=Schema)

        table_info = {
            "schema": Schema,
            "table": table,
            "columns": {},
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }

        for column in columns:
            column_info = {
                "type": type(column['type']).__name__,
                "nullable": column['nullable'],
                "autoincrement": column['autoincrement'],
                "default": column['default'],
                "primary_key": column['name'] in primary_keys
            }
            table_info["columns"][column['name']] = column_info

        return table_info
    except SQLAlchemyError as e:
        logging.error(f"Error retrieving table info: {e}")
        raise

@mcp.tool(
    name="filter_table_names",
    description="Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format "
                "[{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}]."
)
def filter_table_names(q: str) -> str:
    """
    Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format
    [{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}].

    Args:
        q (str): The substring to filter table names by.

    Returns:
        str: A list containing information about tables whose names contain the substring 'q'.
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)

        tables_info = []

        schemas = inspector.get_schema_names()

        # Iterate over each schema to retrieve table names
        for schema_name in schemas:
            tables = inspector.get_table_names(schema=schema_name)
            for table in tables:
                if q in table:
                    tables_info.append({"schema": schema_name, "table": table})

        # return tables_info
        return json.dumps(tables_info)
    except SQLAlchemyError as e:
        logging.error(f"Error filtering table names: {e}")
        raise


@mcp.tool(
    name="execute_query",
    description="Execute a SQL query and return results in JSONL format."
)
def execute_query(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute a SQL query and return results in JSONL format.

    Args:
        query (str): The SQL query to execute.
        max_rows (int): Maximum number of rows to return. Default is 100.
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to pass to the query.

    Returns:
        str: Results in JSONL format.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            # Execute the query with parameters
            rs = connection.execute(text(query), params)
            
            results = []
            
            for row in rs:
                # results.append(dict(row._mapping))
                truncated_row = {key: (str(value)[:MAX_LONG_DATA] if value is not None else None) for key, value in row._mapping.items()}
                results.append(truncated_row)                
                if len(results) >= max_rows:
                    break

        # Convert the results to JSONL format
        jsonl_results = "\n".join(json.dumps(row) for row in results)

        # Return the JSONL formatted results
        return jsonl_results
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        raise


@mcp.tool(
    name="execute_query_md",
    description="Execute a SQL query and return results in Markdown table format."
)
def execute_query_md(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute a SQL query and return results in Markdown table format.

    Args:
        query (str): The SQL query to execute.
        max_rows (int): Maximum number of rows to return. Default is 100.
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to pass to the query.

    Returns:
        str: Results in Markdown table format.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            # Execute the query with parameters
            rs = connection.execute(text(query), params)

            results = []
            columns = rs.keys()

            # Iterate over the result set and convert each row to a dictionary
            for row in rs:
                # results.append(dict(row._mapping))
                truncated_row = {key: (str(value)[:MAX_LONG_DATA] if value is not None else None) for key, value in row._mapping.items()}
                results.append(truncated_row)                
                if len(results) >= max_rows:
                    break

        # Create the Markdown table header
        md_table = "| " + " | ".join(columns) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(columns)) + " |\n"

        # Add rows to the Markdown table
        for row in results:
            md_table += "| " + " | ".join(str(row[col]) for col in columns) + " |\n"

        # Return the Markdown formatted results
        return md_table
    except SQLAlchemyError as e:
        logging.error(f"Error executing query for Markdown: {e}")
        raise

if __name__ == "__main__":
    mcp.run()
