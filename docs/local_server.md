
# Local PeeringDB Mirror Using peeringdb-py (with Additional Notes from `local_setup.md`)

Below is a **comprehensive guide** that combines the instructions for using the **`peeringdb-py`** containerized approach with additional details found in the official [PeeringDB `local_setup.md` docs](https://github.com/peeringdb/peeringdb/blob/master/docs/local_setup.md). The goal is to give you a single reference for:

1. **Setting up a local PeeringDB instance** using the **`peeringdb-py`** tool.
2. **Syncing and maintaining** your local data from the official PeeringDB.
3. **Incorporating best practices** and extra notes from `local_setup.md` (including Docker tips, manual environment setup advice, etc.).

---

## 1. Overview

Running a **local mirror** of PeeringDB lets you:

- Develop or test scripts without hitting `https://api.peeringdb.com` directly.
- Switch API endpoints between your local instance and the official one.
- Have a stable, internal environment that can be kept in sync with the real-world PeeringDB data.

### Methods to Run a Local Instance

There are two primary methods:

1. **Using the `peeringdb-py` Approach**
   - Simplifies setup via a single CLI command: `peeringdb server --setup`.
   - Automatically checks out **Docker Compose** configs to stand up a local PeeringDB + PostgreSQL environment.
   - Provides built-in commands for data load and sync, as well as a process for keeping the data in sync.

2. **Manual / Traditional Setup** (as described in `local_setup.md`)
   - Clone the [PeeringDB repo](https://github.com/peeringdb/peeringdb) and manually configure Django, Python, Docker, etc.
   - More flexible, but slightly more involved.
   - Details in [local_setup.md](https://github.com/peeringdb/peeringdb/blob/master/docs/local_setup.md)

Below, we’ll focus on the **`peeringdb-py`** approach, while pulling in important notes from `local_setup.md` to ensure you have the full picture.

---

## 2. Prerequisites

1. **Python 3.8+** – Required for the `peeringdb-py` CLI.
2. **Docker** (and **Docker Compose** if not already included with your Docker install).
3. **Git** (optional, unless you want to also directly clone or reference PeeringDB’s code).

---

## 3. Install the `peeringdb` Python Package

Install the `peeringdb` Python package (also referred to as `peeringdb-py`) which provides the CLI:

```bash
pip install --upgrade peeringdb
```

## 4. Run the Server Setup

```sh
peeringdb server --setup
```

What --setup Does

1. clones the peeringdb_server git repo to use the current setup script.
2. Uses the cloned docker-compose.yml and environment files to create a local PeeringDB server.
3. loads and syncs data with public data
4. creates an auto sync process to keep it running.
5. starts serving data on http://localhost:8000

Once complete, you should should be able to go to `http://localhost:8000` in your browser and see the PeeringDB interface.


## 5. Using the Local PeeringDB

When your local PeeringDB is ready, you can use the new endpoint in place of the official PeeringDB endpoint.

Depending on how your scripts are written, you may need to adjust the API endpoint they use. For example, if you have a script that hits the PeeringDB API, you might change the endpoint from:

```python
# real endpoint
REAL_PEERINGDB_API_ENDPOINT = "https://www.peeringdb.com/api"

# local endpoint
LOCAL_PEERINGDB_API_ENDPOINT = "http://localhost:8000/api"

PEERINGDB_API_ENDPOINT = os.getenv("PEERINGDB_API_ENDPOINT", LOCAL_PEERINGDB_API_ENDPOINT)
```

If you wish to serve it locally, you can use nginx to reverse proxy the local server to a domain name. This is useful if you have scripts that rely on a domain name to access the API.

For example, you can add something similar to the following to your nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name peeringdb.local;

    error_log   /var/log/nginx/peeringdb-error.log;
    access_log  /var/log/nginx/peeringdb-access.log;

    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
```




