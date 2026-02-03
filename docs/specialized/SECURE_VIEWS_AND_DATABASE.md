# Secure Views & Database Session Variables

## Overview

This document covers the secure views architecture (encrypted data access) and MySQL session variables for decryption. Base tables store encrypted data; secure views decrypt at read time using `@aesKey`.

---

## 1. Secure Views Architecture

### The Problem

LLMs were told to "use secure_* views" but didn't know which tables have them, leading to hallucinated tables like `secure_inspections` (doesn't exist).

### The Solution: Explicit Mapping

**Location**: `src/config/constants.py` (SECURE_VIEW_MAP), `src/utils/sql/secure_views.py` (rewriting logic)

```python
# Single source of truth - only these get secure_* variants
SECURE_VIEW_MAP = {
    "user": "secure_user",
    "customerLocation": "secure_customerlocation",
    "customerContact": "secure_customercontact",
    "employee": "secure_employee",
    "workOrder": "secure_workorder",
    "customer": "secure_customer",
}
```

**Critical rule**: Only tables in this map get `secure_*` variants. All others use base table names.

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

1. Add to `SECURE_VIEW_MAP` in `src/config/constants.py`
2. Create the view in MySQL with `AES_DECRYPT(..., @aesKey)`
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

- `src/config/constants.py` – `SECURE_VIEW_MAP`, `SECURE_VIEWS`
- `src/utils/sql/secure_views.py` – `rewrite_secure_tables()`, `validate_tables_exist()`
- `src/infra/database.py` – Session variable listener
- `src/tools/sql_tool.py` – Uses secure view rewriting
