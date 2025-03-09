# MUN Connect - Docker & Supabase Setup

A Next.js application for Model United Nations conferences with Supabase backend integration.

## 📋 Prerequisites

- Docker and Docker Compose
- Node.js 18 or higher (for local development)
- Git

## 🚀 Getting Started

### Clone the Repository

```bash
git clone <your-repository-url>
cd mun-connect
```

### Environment Setup

The project uses Docker containers with Supabase for the database. All environment variables are stored in the `.env` file.

### Starting the Application

```bash
# Start all containers in detached mode
docker-compose up -d
```

This command will start:
- Next.js application on http://localhost:3000
- Supabase PostgreSQL database
- MCP Server for database operations
- pgAdmin for database management on http://localhost:5050

### Accessing pgAdmin

1. Navigate to http://localhost:5050 in your browser
2. Log in with:
   - Email: admin@example.com
   - Password: pgadmin
3. To connect to the Supabase database:
   - Right-click on Servers → Create → Server
   - Name: Supabase Local
   - Connection tab:
     - Host: supabase_postgres
     - Port: 5432
     - Username: postgres
     - Password: (from .env file)

## 🛠️ Database Management

### Initialize the Database

We've included a script to initialize the database with sample data:

```bash
./init-db.sh
```

### Run SQL Queries

You can run SQL queries against the database using:

```bash
./run-sql.sh "SELECT * FROM committees;"
```

## 🧪 Testing the Supabase Connection

To test your Supabase connection, run:

```bash
# Install dependencies if needed
npm install dotenv @supabase/supabase-js

# Run the test script
node supabase-test.js
```

## 🗄️ Data Schema

The sample database includes:

- **Committees**: Conference committees
- **Delegates**: Participants assigned to committees
- **Resolutions**: Documents created by committees

## 🛑 Stopping the Application

```bash
docker-compose down
```

To remove volumes (all data will be lost):

```bash
docker-compose down -v
```

## 🔄 Troubleshooting

1. **Connection Issues**: Ensure all containers are running with `docker ps`
2. **Database Access**: Check credentials in the `.env` file
3. **Container Logs**: View logs with `docker logs <container_name>`

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.io/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Documentation](https://docs.docker.com)
