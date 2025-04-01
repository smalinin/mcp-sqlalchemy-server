from collections import defaultdict
from datetime import datetime, date
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import VARCHAR, String, bindparam, create_engine, inspect, text
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
API_KEY = os.getenv("API_KEY", "none")

### Database ###

def get_engine(readonly=True, url:Optional[str]=None):
    connection_string = os.getenv('DB_URL')

    if url is not None:
        connection_string = url

    if not connection_string:
        logging.error("DB_URL environment variable is not set.")
        raise ValueError("DB_URL environment variable is not set.")
    
    # logging.info(f"DB_URL: {connection_string}")
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
    name="podbc_get_schemas",
    description="Retrieve and return a list of all schema names from the connected database."
)
def podbc_get_schemas(url:Optional[str]=None) -> str:
    """
    Retrieve and return a list of all schema names from the connected database.

    Args:
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: A list of schema names.
    """
    try:
        engine = get_engine(True, url)

        query = text("""
            SELECT DISTINCT name_part(KEY_TABLE, 0) AS CATALOG_NAME
            FROM DB.DBA.SYS_KEYS
            WHERE __any_grants(KEY_TABLE)
            AND table_type(KEY_TABLE) = 'TABLE'
            AND KEY_IS_MAIN = 1
            AND KEY_MIGRATE_TO IS NULL
        """)

        with engine.connect() as conn:
            result = conn.execute(query)
            catalogs = {row.CATALOG_NAME for row in result.fetchall()}
            return json.dumps(list(catalogs))

    except SQLAlchemyError as e:
        logging.error(f"Error retrieving schemas: {e}")
        raise


@mcp.tool(
    name="podbc_get_tables",
    description="Retrieve and return a list containing information about tables in specified schema, if empty uses connection default"
)
def podbc_get_tables(Schema: Optional[str] = None, url:Optional[str]=None) -> str:
    """
    Retrieve and return a list containing information about tables.

    If `schema` is None, returns tables for all schemas.
    If `schema` is not None, returns tables for the specified schema.

    Args:
        schema (Optional[str]): The name of the schema to retrieve tables for. If None, retrieves tables for all schemas.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: A list containing information about tables.
    """
    _schema = "%" if Schema is None else Schema
    params = {"cat":_schema}
    try:
        engine = get_engine(True, url)

        query = text("""
            SELECT 
            name_part(KEY_TABLE,0) AS TABLE_CAT VARCHAR(128),
	        name_part(KEY_TABLE,1) AS TABLE_SCHEM VARCHAR(128),
	        name_part(KEY_TABLE,2) AS TABLE_NAME VARCHAR(128)
        FROM DB.DBA.SYS_KEYS 
        WHERE __any_grants(KEY_TABLE) AND 
	    UPPER(name_part(KEY_TABLE,0)) LIKE UPPER(:cat) AND 
	    locate (concat ('G', table_type (KEY_TABLE)), 'GTABLEGVIEW') > 0 AND 
	    KEY_IS_MAIN = 1 AND
	    KEY_MIGRATE_TO IS NULL
        ORDER BY 2, 3
        """)

        with engine.connect() as conn:
            rs = conn.execute(query, params)

            results = []
            for row in rs:
                results.append(dict(row._mapping))

            return json.dumps(results, indent=2)

    except SQLAlchemyError as e:
        logging.error(f"Error retrieving tables: {e}")
        raise
        

@mcp.tool(
    name="podbc_describe_table",
    description="Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable,"
                " autoincrement, primary key, and foreign keys."
)
def podbc_describe_table(Schema:str, table: str, url:Optional[str]=None) -> str:
    """
    Retrieve and return a dictionary containing the definition of a table, including column names, data types, nullable, autoincrement, primary key, and foreign keys.

    If `schema` is None, returns the table definition for the specified table in all schemas.
    If `schema` is not None, returns the table definition for the specified table in the specified schema.

    Args:
        schema (str): The name of the schema to retrieve the table definition for. If None, retrieves the table definition for all schemas.
        table (str): The name of the table to retrieve the definition for.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: A dictionary containing the table definition, including column names, data types, nullable, autoincrement, primary key, and foreign keys.
    """
    try:
        engine = get_engine(True, url)
        table_definition = {}
        cat = "%" if Schema is None else Schema

        with engine.connect() as conn:
            rc, tbl = _has_table(conn, cat=cat, table=table)
            if rc:
                table_definition = _get_table_info(conn, cat=tbl.get("cat"), sch=tbl.get("sch"), table=tbl.get("name"))

        return json.dumps(table_definition, indent=2)
    except SQLAlchemyError as e:
        logging.error(f"Error retrieving table definition: {e}")
        raise


def _has_table(conn, cat:str, table:str) -> bool:
    params = {"cat":cat, "tbl":table}

    query = text("""
        SELECT 
            name_part(KEY_TABLE,0) AS TABLE_CAT VARCHAR(128),
	        name_part(KEY_TABLE,1) AS TABLE_SCHEM VARCHAR(128),
	        name_part(KEY_TABLE,2) AS TABLE_NAME VARCHAR(128)
        FROM DB.DBA.SYS_KEYS 
        WHERE __any_grants(KEY_TABLE) AND 
	        UPPER(name_part(KEY_TABLE,0)) LIKE UPPER(:cat) AND 
	        UPPER(name_part(KEY_TABLE,2)) LIKE UPPER(:tbl) AND 
	        locate (concat ('G', table_type (KEY_TABLE)), 'GTABLEGVIEW') > 0 AND 
	        KEY_IS_MAIN = 1 AND
	        KEY_MIGRATE_TO IS NULL
    """)

    row = conn.execute(query, params).fetchone()
    if row:
        return True, {"cat":row.TABLE_CAT, "sch": row.TABLE_SCHEM, "name":row.TABLE_NAME}
    else:
        return False, {}
    

def _get_columns(conn, cat: str, sch: str, table:str):
    params = {"cat":cat, "sch":sch, "tbl":table}

    query = text("""
        select
            name_part (k.KEY_TABLE,0) AS TABLE_CAT VARCHAR(128),
            name_part (k.KEY_TABLE,1) AS TABLE_SCHEM VARCHAR(128),
            name_part (k.KEY_TABLE,2) AS TABLE_NAME VARCHAR(128),
            c."COLUMN" AS COLUMN_NAME VARCHAR(128),
            dv_to_sql_type3(c.COL_DTP) AS DATA_TYPE SMALLINT,
            case when (c.COL_DTP in (125, 132) and get_keyword ('xml_col', coalesce (c.COL_OPTIONS, vector ())) is not null) then 'XMLType' else dv_type_title(c.COL_DTP) end AS TYPE_NAME VARCHAR(128),
            c.COL_PREC AS COLUMN_SIZE INTEGER,
            c.COL_PREC AS BUFFER_LENGTH INTEGER,
            c.COL_SCALE AS DECIMAL_DIGITS SMALLINT,
            2 AS NUM_PREC_RADIX SMALLINT,
            case c.COL_NULLABLE when 1 then 0 else 1 end AS NULLABLE SMALLINT,
            NULL AS REMARKS VARCHAR(254),
            deserialize (c.COL_DEFAULT) AS COLUMN_DEF VARCHAR(254),
            case 1 when 1 then dv_to_sql_type3(c.COL_DTP) else dv_to_sql_type(c.COL_DTP) end AS SQL_DATA_TYPE SMALLINT,
            case c.COL_DTP when 129 then 1 when 210 then 2 when 211 then 3 else NULL end AS SQL_DATETIME_SUB SMALLINT,
            c.COL_PREC AS CHAR_OCTET_LENGTH INTEGER,
            cast ((select count(*) from DB.DBA.SYS_COLS where \\TABLE = k.KEY_TABLE and COL_ID <= c.COL_ID) as INTEGER) AS ORDINAL_POSITION INTEGER,
            case c.COL_NULLABLE when 1 then 'NO' else 'YES' end AS IS_NULLABLE VARCHAR,
            c.COL_CHECK as COL_CHECK
        from DB.DBA.SYS_KEYS k, DB.DBA.SYS_KEY_PARTS kp, DB.DBA.SYS_COLS c 
        where upper (name_part (k.KEY_TABLE,0)) like upper (:cat)
            and upper (name_part (k.KEY_TABLE,1)) = upper (:sch)
            and upper (name_part (k.KEY_TABLE,2)) = upper (:tbl)
            and c.\"COLUMN\" <> '_IDN'
            and k.KEY_IS_MAIN = 1
            and k.KEY_MIGRATE_TO is null
            and kp.KP_KEY_ID = k.KEY_ID
            and COL_ID = KP_COL
            order by KEY_TABLE, 17
        """)

    ret = []
    for row in conn.execute(query, params):
        ret.append(
            { "name": row.COLUMN_NAME,
             "type": row.TYPE_NAME,
             "nullable": bool(row.NULLABLE),
             "default": row.COLUMN_DEF,
             "autoincrement": row.COL_CHECK.find("I")!=-1,
            })
    return ret


def _get_pk_constraint(conn, cat: str, sch: str, table:str):
    params = {"cat":cat, "sch":sch, "tbl":table}

    query = text("""
        select
            name_part(v1.KEY_TABLE,0) AS \\TABLE_QUALIFIER VARCHAR(128),
            name_part(v1.KEY_TABLE,1) AS \\TABLE_OWNER VARCHAR(128),
            name_part(v1.KEY_TABLE,2) AS \\TABLE_NAME VARCHAR(128),
            DB.DBA.SYS_COLS.\\COLUMN AS \\COLUMN_NAME VARCHAR(128),
            (kp.KP_NTH+1) AS \\KEY_SEQ SMALLINT,
            name_part (v1.KEY_NAME, 2) AS \\PK_NAME VARCHAR(128),
            name_part(v2.KEY_TABLE,0) AS \\ROOT_QUALIFIER VARCHAR(128),
            name_part(v2.KEY_TABLE,1) AS \\ROOT_OWNER VARCHAR(128),
            name_part(v2.KEY_TABLE,2) AS \\ROOT_NAME VARCHAR(128)
        from DB.DBA.SYS_KEYS v1, DB.DBA.SYS_KEYS v2,
             DB.DBA.SYS_KEY_PARTS kp, DB.DBA.SYS_COLS
        where upper(name_part(v1.KEY_TABLE,0)) like upper(:cat)
            and upper(name_part(v1.KEY_TABLE,1)) = upper(:sch)
            and upper(name_part(v1.KEY_TABLE,2)) = upper(:tbl)
            and v1.KEY_IS_MAIN = 1
            and v1.KEY_MIGRATE_TO is NULL
            and v1.KEY_SUPER_ID = v2.KEY_ID
            and kp.KP_KEY_ID = v1.KEY_ID
            and kp.KP_NTH < v1.KEY_DECL_PARTS
            and DB.DBA.SYS_COLS.COL_ID = kp.KP_COL
            and DB.DBA.SYS_COLS.\\COLUMN <> '_IDN'
        order by v1.KEY_TABLE, kp.KP_NTH
    """)

    data = conn.execute(query, params).fetchall();

    ret = None
    if len(data) > 0:
        ret = { "constrained_columns": [row.COLUMN_NAME for row in data],
                "name": data[0].PK_NAME,
              }
    return ret


def _get_foreign_keys(conn, cat: str, sch: str, table:str):
    params = {"cat":cat, "sch":sch, "tbl":table}

    query = text("""
        select
            name_part (PK_TABLE, 0) as PKTABLE_QUALIFIER varchar (128),
            name_part (PK_TABLE, 1) as PKTABLE_OWNER varchar (128),
            name_part (PK_TABLE, 2) as PKTABLE_NAME varchar (128),
            PKCOLUMN_NAME as PKCOLUMN_NAME varchar (128),
            name_part (FK_TABLE, 0) as FKTABLE_QUALIFIER varchar (128),
            name_part (FK_TABLE, 1) as FKTABLE_OWNER varchar (128),
            name_part (FK_TABLE, 2) as FKTABLE_NAME varchar (128),
            FKCOLUMN_NAME as FKCOLUMN_NAME varchar (128),
            (KEY_SEQ + 1) as KEY_SEQ SMALLINT,
            FK_NAME as FK_NAME varchar (128),
            PK_NAME as PK_NAME varchar (128)
        from DB.DBA.SYS_FOREIGN_KEYS
        where upper (name_part (FK_TABLE, 0)) like upper (:cat)
            and upper (name_part (FK_TABLE, 1)) = upper (:sch)
            and upper (name_part (FK_TABLE, 2)) = upper (:tbl)
        order by 1, 2, 3, 5, 6, 7, 9
    """)

    def fkey_rec():
        return {
            "name": None,
            "constrained_columns": [],
            "referred_cat": None,
            "referred_schem": None,
            "referred_table": None,
            "referred_columns": [],
            "options": {},
        }

    fkeys = defaultdict(fkey_rec)

    crs = conn.execute(query, params)
    for row in crs:
      rec = fkeys[row.FK_NAME]
      rec["name"] = row.FK_NAME

      c_cols = rec["constrained_columns"]
      c_cols.append(row.FKCOLUMN_NAME)

      r_cols = rec["referred_columns"]
      r_cols.append(row.PKCOLUMN_NAME)

      if not rec["referred_table"]:
        rec["referred_table"] = row.PKTABLE_NAME
        rec["referred_schem"] = row.PKTABLE_OWNER
        rec["referred_cat"] = row.PKTABLE_QUALIFIER

    return list(fkeys.values())


def _get_table_info(conn, cat:str, sch: str, table: str) -> Dict[str, Any]:
    """
    Helper function to retrieve table information including columns and constraints.

    Args:
        conn: connection.
        schema (str): The name of the schema.
        table (str): The name of the table.

    Returns:
        Dict[str, Any]: A dictionary containing the table definition, including column names, data types, nullable, autoincrement, primary key, and foreign keys.
    """
    try:
        columns = _get_columns(conn, cat=cat, sch=sch, table=table)
        primary_keys = _get_pk_constraint(conn, cat=cat, sch=sch, table=table)['constrained_columns']
        foreign_keys = _get_foreign_keys(conn, cat=cat, sch=sch, table=table)

        table_info = {
            "TABLE_CAT": cat,
            "TABLE_SCHEM": sch,
            "TABLE_NAME": table,
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
    name="podbc_filter_table_names",
    description="Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format "
                "[{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}]."
)
def podbc_filter_table_names(q: str, url:Optional[str]=None) -> str:
    """
    Retrieve and return a list containing information about tables whose names contain the substring 'q' in the format
    [{'schema': 'schema_name', 'table': 'table_name'}, {'schema': 'schema_name', 'table': 'table_name'}].

    Args:
        q (str): The substring to filter table names by.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: A list containing information about tables whose names contain the substring 'q'.
    """
    try:
        engine = get_engine(True, url)

        query = text("""
            SELECT 
            name_part(KEY_TABLE,0) AS TABLE_CAT VARCHAR(128),
	        name_part(KEY_TABLE,1) AS TABLE_SCHEM VARCHAR(128),
	        name_part(KEY_TABLE,2) AS TABLE_NAME VARCHAR(128)
        FROM DB.DBA.SYS_KEYS 
        WHERE __any_grants(KEY_TABLE) AND 
	    locate (concat ('G', table_type (KEY_TABLE)), 'GTABLEGVIEW') > 0 AND 
	    KEY_IS_MAIN = 1 AND
	    KEY_MIGRATE_TO IS NULL
        ORDER BY 2, 3
        """)

        results = []

        with engine.connect() as conn:
            rs = conn.execute(query)

            # Iterate over each schema to retrieve table names
            for row in rs:
                if q in row.TABLE_NAME:
                    results.append(dict(row._mapping))

        return json.dumps(results, indent=2)
    except SQLAlchemyError as e:
        logging.error(f"Error filtering table names: {e}")
        raise


@mcp.tool(
    name="podbc_execute_query",
    description="Execute a SQL query and return results in JSONL format."
)
def podbc_execute_query(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None,
                  url:Optional[str]=None) -> str:
    """
    Execute a SQL query and return results in JSONL format.

    Args:
        query (str): The SQL query to execute.
        max_rows (int): Maximum number of rows to return. Default is 100.
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to pass to the query.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results in JSONL format.
    """
    try:
        engine = get_engine(True, url)
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
    name="podbc_execute_query_md",
    description="Execute a SQL query and return results in Markdown table format."
)
def podbc_execute_query_md(query: str, max_rows: int = 100, params: Optional[Dict[str, Any]] = None, 
                     url:Optional[str]=None) -> str:
    """
    Execute a SQL query and return results in Markdown table format.

    Args:
        query (str): The SQL query to execute.
        max_rows (int): Maximum number of rows to return. Default is 100.
        params (Optional[Dict[str, Any]]): Optional dictionary of parameters to pass to the query.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results in Markdown table format.
    """
    try:
        engine = get_engine(True, url)
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


@mcp.tool(
    name="podbc_query_database",
    description="Execute a SQL query and return results in JSONL format."
)
def podbc_query_database(query: str, url:Optional[str]=None) -> str:
    """
    Execute a SQL query and return results in JSONL format.

    Args:
        query (str): The SQL query to execute.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results in JSONL format.
    """
    try:
        engine = get_engine(True, url)
        with engine.connect() as connection:
            # Execute the query with parameters
            rs = connection.execute(text(query))
            
            results = []
            
            for row in rs:
                # results.append(dict(row._mapping))
                truncated_row = {key: (str(value)[:MAX_LONG_DATA] if value is not None else None) for key, value in row._mapping.items()}
                results.append(truncated_row)                

        # Convert the results to JSONL format
        jsonl_results = "\n".join(json.dumps(row) for row in results)

        # Return the JSONL formatted results
        return jsonl_results
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        raise


@mcp.tool(
    name="podbc_spasql_query",
    description="Execute a SPASQL query and return results."
)
def podbc_spasql_query(query: str, max_rows:Optional[int] = 20, timeout:Optional[int] = 300000,  url:Optional[str]=None) -> str:
    """
    Execute a SPASQL query and return results in JSONL format.

    Args:
        query (str): The SPASQL query to execute.
        max_rows (int): Maximum number of rows to return. Default is 100.
        timeout (int): Query timeout. Default is 30000ms.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results in requested format as string.
    """
    try:
        engine = get_engine(True, url)
        with engine.connect() as connection:
            # Execute the query with parameters
            cmd = text("select Demo.demo.execute_spasql_query(:query, :limit, :timeout) as result")
            cmd = cmd.bindparams(
                bindparam("query", type_=VARCHAR, literal_execute=True, value=query),
                bindparam("limit", value=max_rows),
                bindparam("timeout", value=timeout),
            )
            rs = connection.execute(cmd).fetchone()
            return rs[0]
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        raise



@mcp.tool(
    name="podbc_sparql_query",
    description="Execute a SPARQL query and return results."
)
def podbc_sparql_query(query: str, format:Optional[str]="json", timeout:Optional[int]= 300000,  url:Optional[str]=None) -> str:
    """
    Execute a SPARQL query and return results.

    Args:
        query (str): The SPARQL query to execute.
        format (str): Maximum number of rows to return. Default is "json".
        timeout (int): Query timeout. Default is 300000ms.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results in requested format as string.
    """
    try:
        engine = get_engine(True, url)
        with engine.connect() as connection:
            # Execute the query with parameters
            cmd = text('select "UB".dba."sparqlQuery"(:query, :fmt, :timeout) as result')
            cmd = cmd.bindparams(
                bindparam("query", type_=VARCHAR, literal_execute=True, value=query),
                bindparam("fmt", value=format),
                bindparam("timeout", value=timeout),
            )
            rs = connection.execute(cmd).fetchone()
            return rs[0]
    except SQLAlchemyError as e:
        logging.error(f"Error executing query: {e}")
        raise


@mcp.tool(
    name="podbc_virtuoso_support_ai",
    description="Tool to use the Virtuoso AI support function"
)
def podbc_virtuoso_support_ai(prompt: str, api_key:Optional[str]=None, url:Optional[str]=None) -> str:
    """
    Tool to use the Virtuoso AI support function

    Args:
        prompt (str): AI prompt text (required).
        api_key (str): API key for AI service (optional).
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results data in JSON.
    """
    try:
        _api_key = api_key if api_key is not None else API_KEY
        engine = get_engine(True, url)
        with engine.connect() as connection:
            # Execute the query with parameters
            cmd = text('select DEMO.DBA.OAI_VIRTUOSO_SUPPORT_AI(:prompt, :key) as result')
            cmd = cmd.bindparams(
                # bindparam("prompt", type_=VARCHAR, literal_execute=True, value=prompt),
                bindparam("prompt", value=prompt),
                bindparam("key", value=_api_key),
            )
            rs = connection.execute(cmd).fetchone()
            return rs[0]
    except SQLAlchemyError as e:
        logging.error(f"Error executing request")
        raise


@mcp.tool(
    name="podbc_sparql_func",
    description="Call ???."
)
def podbc_sparql_func(prompt: str, api_key:Optional[str]=None, url:Optional[str]=None) -> str:
    """
    Call OpenAI func.

    Args:
        prompt (str): The prompt.
        api_key (str): optional.
        url (Optional[str]=None): Optional url connection string.

    Returns:
        str: Results data in JSON.
    """
    try:
        _api_key = api_key if api_key is not None else API_KEY
        engine = get_engine(True, url)
        with engine.connect() as connection:
            # Execute the query with parameters
            cmd = text('select DEMO.DBA.OAI_SPARQL_FUNC(:prompt,:key) as result')             
            cmd = cmd.bindparams(
                # bindparam("prompt", type_=VARCHAR, literal_execute=True, value=prompt),
                bindparam("prompt", value=prompt),
                bindparam("key", value=_api_key),
            )
            rs = connection.execute(cmd).fetchone()
            return rs[0]
    except SQLAlchemyError as e:
        logging.error(f"Error executing request")
        raise





if __name__ == "__main__":
    mcp.run()
