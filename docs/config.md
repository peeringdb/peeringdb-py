
# PeeringDB Client Configuration

This document describes the environment variables used to configure the PeeringDB client.

## Sync Configuration

- **PDB_SYNC_URL**: The main URL for syncing with PeeringDB. Default is `https://www.peeringdb.com/api`.
- **PDB_SYNC_CACHE_URL**: The cache URL for syncing with PeeringDB. Default is `https://public.peeringdb.com`.
- **PDB_SYNC_CACHE_DIR**: The directory for caching PeeringDB data. Default is `~/.cache/peeringdb`.
- **PDB_SYNC_API_KEY**: The API key for authentication. No default value.
- **PDB_SYNC_USER**: The username for authentication. No default value.
- **PDB_SYNC_PASSWORD**: The password for authentication. No default value.
- **PDB_SYNC_STRIP_TZ**: Strip timezone information (1 for true, 0 for false). Default is `1`.
- **PDB_SYNC_ONLY**: Comma-separated list of data to sync. Default is all data (empty list).
- **PDB_SYNC_TIMEOUT**: The timeout for syncing operations in seconds. Default is `0` (no timeout).

## ORM Configuration

### Database Configuration

- **PDB_ORM_DB_ENGINE**: The database engine to use. Default is `sqlite3`.
- **PDB_ORM_DB_NAME**: The name of the database. Default is `peeringdb.sqlite3`.
- **PDB_ORM_DB_HOST**: The host of the database. No default value.
- **PDB_ORM_DB_PORT**: The port of the database. Default is `0`.
- **PDB_ORM_DB_USER**: The username for database authentication. No default value.
- **PDB_ORM_DB_PASSWORD**: The password for database authentication. No default value.

### General ORM Configuration

- **PDB_ORM_BACKEND**: The backend to use for the ORM. Default is `django_peeringdb`.