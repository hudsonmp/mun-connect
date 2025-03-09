#!/bin/bash

# Load environment variables
source .env

# Function to connect to database using psql
function connect() {
    docker exec -it supabase_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}
}

# Function to dump the database schema
function dump_schema() {
    docker exec -it supabase_postgres pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} --schema-only > schema_dump.sql
    echo "Schema dumped to schema_dump.sql"
}

# Function to list all tables
function list_tables() {
    docker exec -it supabase_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "\dt"
}

# Function to execute SQL query
function execute_sql() {
    if [ -z "$1" ]; then
        echo "Usage: ./db-tools.sh execute_sql \"SELECT * FROM your_table;\""
        return 1
    fi
    
    docker exec -it supabase_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "$1"
}

# Display help if no arguments provided
if [ $# -eq 0 ]; then
    echo "Supabase Database Tools"
    echo "Usage: ./db-tools.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  connect         - Connect to database using psql"
    echo "  dump_schema     - Dump database schema to file"
    echo "  list_tables     - List all tables in database"
    echo "  execute_sql     - Execute SQL query (requires query as argument)"
    exit 0
fi

# Execute the requested command
case "$1" in
    connect)
        connect
        ;;
    dump_schema)
        dump_schema
        ;;
    list_tables)
        list_tables
        ;;
    execute_sql)
        execute_sql "$2"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run ./db-tools.sh without arguments to see usage."
        exit 1
        ;;
esac 