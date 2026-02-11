# Secure Views & Database Session Variables

## Overview

This document covers the secure views architecture (encrypted data access) and MySQL session variables for decryption. Base tables store encrypted data; secure views decrypt at read time using `@aesKey`.

---

## 1. Secure Views Architecture

### The Problem

LLMs were told to "use secure_* views" but didn't know which tables have them, leading to hallucinated tables like `secure_inspections` (doesn't exist).

### The Solution: Explicit Mapping (Dynamic Discovery)

**Location**: `src/utils/sql/secure_views.py` (mapping discovery and rewriting logic)

The secure view mapping is **discovered from the database at runtime**, not hardcoded. Base tables that require secure views are listed in the `SECURE_BASE_TABLES` environment variable (comma-separated). On startup, the system queries the database for views whose names start with `secure_` and matches them to these base tables (e.g. `employee` → `secure_employee`). Use `get_secure_view_map()` and `get_secure_views()` from this module.

**Configuration** (`.env`):
```bash
SECURE_BASE_TABLES=user,customer,customerLocation,customerContact,employee,workOrder
```

**Critical rule**: Only base tables listed in `SECURE_BASE_TABLES` (with a matching `secure_*` view in MySQL) get rewritten. All others use base table names.

### Workflow

```
User Question
    ↓
[SQL Generator] – generates SQL with logical names (employee, workOrder)
    ↓
[Rewriter] – deterministically rewrites to secure views
    ↓
[Validator] – ensures all tables exist (catches hallucinations)
    ↓
[Executor] – runs the query
```

### Example

**LLM generates:**
```sql
SELECT firstName, lastName FROM employee WHERE id = 1
```

**After rewriting:**
```sql
SELECT firstName, lastName FROM secure_employee WHERE id = 1
```

### Adding New Secure Views

1. Create the view in MySQL with `AES_DECRYPT(..., @aesKey)` (name must be `secure_<basename>`).
2. Add the base table to `SECURE_BASE_TABLES` in `.env` (comma-separated).
3. Rebuild join graph: `uv run python scripts/build_join_graph.py`
4. Test: `uv run python scripts/test_secure_views.py`

---

## 2. MySQL Session Variables

### Problem

Secure views use `AES_DECRYPT(encryptedField, @aesKey)`. The view cannot decrypt without `@aesKey` being set in the session.

### Solution

SQLAlchemy event listeners set session variables when connections are established:

**Location**: `src/infra/database.py`

```python
@event.listens_for(engine, "connect")
def set_session_variables(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    encrypt_key = os.getenv("DB_ENCRYPT_KEY", "")
    cursor.execute(f"SET @aesKey = '{encrypt_key}'")
    cursor.execute("SET @customerIds = NULL")
    cursor.execute("SET @workOrderIds = NULL")
    cursor.execute("SET @serviceLocationIds = NULL")
    cursor.close()
```

### Configuration

```bash
# .env
DB_ENCRYPT_KEY=your_encryption_key_here
```

**Security**: Keep this key secret. Never commit to version control.

### Session Variables Reference

| Variable | Purpose |
|----------|---------|
| `@aesKey` | Encryption key for `AES_DECRYPT` (from `DB_ENCRYPT_KEY`) |
| `@customerIds` | Filter data by customer IDs (future: user context) |
| `@workOrderIds` | Filter data by work order IDs (future: request context) |
| `@serviceLocationIds` | Filter by service location (future: permissions) |

### Benefits

- Automatic on every connection checkout
- No query wrapping needed
- Connection pooling compatible
- Works transparently with the SQL agent

---

## Related Files

- `src/utils/sql/secure_views.py` – `get_secure_view_map()`, `get_secure_views()`, `initialize_secure_view_map()`, `rewrite_secure_tables()`, `validate_tables_exist()`
- `src/infra/database.py` – Session variable listener
- `src/tools/sql_tool.py` – Uses secure view rewriting
