# MySQL Session Variables for Secure Views

## Overview

This document explains how the Python AI Agent sets MySQL session variables to enable secure views to decrypt encrypted data, mirroring the approach used in the Node.js API.

## Problem Statement

The MySQL database uses `AES_ENCRYPT()` to encrypt sensitive fields in base tables:
- `user` (encrypted fields)
- `customer` (encrypted fields)
- `customerLocation` (encrypted fields)
- `customerContact` (encrypted fields)
- `employee` (encrypted fields)
- `workOrder` (encrypted fields)

Secure views (e.g., `secure_user`, `secure_customer`) use `AES_DECRYPT()` to decrypt these fields:

```sql
CREATE VIEW secure_user AS
SELECT 
    id,
    AES_DECRYPT(encryptedName, @aesKey) AS name,
    AES_DECRYPT(encryptedEmail, @aesKey) AS email,
    -- other fields
FROM user;
```

**The Problem**: Views cannot decrypt without the encryption key being available as a MySQL session variable (`@aesKey`).

## Solution Architecture

### Node.js Approach (Reference)

The Node.js API sets session variables before each query:

```javascript
// 1. Set session variables
await db.sequelize.query("SET @aesKey = 'encryption_key'", { transaction });
await db.sequelize.query("SET @customerIds = NULL", { transaction });
await db.sequelize.query("SET @serviceLocationIds = NULL", { transaction });

// 2. Run main query (views can now use @aesKey)
const data = await db.sequelize.query(mainQuery, { transaction });

// 3. Cleanup
await db.sequelize.query("SET @aesKey = NULL", { transaction });
```

### Python Implementation

We use **SQLAlchemy event listeners** to automatically set session variables when connections are established from the pool:

```python
@event.listens_for(engine, "connect")
def set_session_variables(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    
    # Set encryption key for AES_DECRYPT in views
    encrypt_key = os.getenv("DB_ENCRYPT_KEY", "")
    cursor.execute(f"SET @aesKey = '{encrypt_key}'")
    
    # Initialize other variables
    cursor.execute("SET @customerIds = NULL")
    cursor.execute("SET @workOrderIds = NULL")
    cursor.execute("SET @serviceLocationIds = NULL")
    
    cursor.close()
```

**Advantages**:
- ✅ Automatic - runs on every connection checkout
- ✅ No query wrapping needed - cleaner code
- ✅ Works with LangChain SQL agent transparently
- ✅ Connection pooling compatible
- ✅ No cleanup needed (variables scoped to connection/session)

## Configuration

### Environment Variables

```bash
# .env
DB_ENCRYPT_KEY=your_encryption_key_here
```

**Security Note**: Keep this key secret! Never commit to version control.

### Code Location

**File**: `apps/backend/src/models/database.py`

```python
class Database:
    def __init__(self, config: DatabaseConfig = None):
        # ... create engine ...
        
        # Register event listener
        self._register_session_variable_listener()
    
    def _register_session_variable_listener(self):
        @event.listens_for(self.engine, "connect")
        def set_session_variables(dbapi_conn, connection_record):
            # Sets @aesKey, @customerIds, etc.
            ...
```

## Session Variables Reference

| Variable | Type | Purpose | Set By |
|----------|------|---------|--------|
| `@aesKey` | String | Encryption key for AES_DECRYPT | Environment (`DB_ENCRYPT_KEY`) |
| `@customerIds` | String/NULL | Filter data by customer IDs | Future: User context |
| `@workOrderIds` | String/NULL | Filter data by work order IDs | Future: Request context |
| `@serviceLocationIds` | String/NULL | Filter data by service location | Future: User permissions |

## Usage in Secure Views

Views can reference these variables directly:

```sql
CREATE VIEW secure_customer AS
SELECT 
    id,
    AES_DECRYPT(customerName, @aesKey) AS customerName,
    AES_DECRYPT(email, @aesKey) AS email,
    AES_DECRYPT(phone, @aesKey) AS phone,
    -- Filter by customer IDs if provided
    CASE 
        WHEN @customerIds IS NOT NULL 
        THEN FIND_IN_SET(id, @customerIds) > 0
        ELSE TRUE
    END AS _filtered
FROM customer
HAVING _filtered = TRUE;
```

## SQL Agent Integration

The SQL agent automatically benefits from these session variables:

```python
# User asks: "Show me customer names"
# SQL Agent generates:
SELECT customerName FROM secure_customer LIMIT 100;

# MySQL executes with @aesKey already set
# Result: Decrypted customer names returned
```

**No code changes needed** - session variables are set transparently at the connection level.

## Comparison: Node.js vs Python

| Aspect | Node.js (Transaction-scoped) | Python (Connection-scoped) |
|--------|------------------------------|---------------------------|
| **Timing** | Before each query | On connection checkout |
| **Scope** | Transaction | Connection/Session |
| **Cleanup** | Manual (SET to NULL) | Automatic (connection return) |
| **Code Complexity** | Higher (wrap every query) | Lower (event listener) |
| **Safety** | Explicit cleanup | Auto cleanup on connection return |
| **Performance** | 3 extra queries per request | 4 queries per connection (pooled) |

### Performance Analysis

**Node.js**: 100 queries/day
- 100 × 3 SET statements = 300 extra queries/day
- 100 × 3 cleanup statements = 300 extra queries/day
- **Total**: 600 extra queries/day

**Python**: 100 queries/day, pool size 5, avg 10 connections/day
- 10 connections × 4 SET statements = 40 extra queries/day
- No cleanup queries (auto on connection close)
- **Total**: 40 extra queries/day (93% reduction)

## Future Enhancements

### 1. User Context Variables

Set `@customerIds` based on authenticated user:

```python
def set_user_context(user_id: str, customer_ids: str):
    """Set user-specific session variables"""
    with engine.connect() as conn:
        conn.execute(text(f"SET @customerIds = '{customer_ids}'"))
```

### 2. Dynamic Variable Setting

Allow SQL agent to set variables based on query context:

```python
# Before: "Show work orders for customer 123"
# Set: @customerIds = '123'
# Query: SELECT * FROM secure_workorder WHERE customerId IN (...)
```

### 3. Row-Level Security

Enhance views to filter by user permissions:

```sql
CREATE VIEW secure_workorder_filtered AS
SELECT *
FROM secure_workorder
WHERE 
    (@customerIds IS NULL OR FIND_IN_SET(customerId, @customerIds) > 0)
    AND (@serviceLocationIds IS NULL OR FIND_IN_SET(serviceLocationId, @serviceLocationIds) > 0);
```

## Testing Session Variables

### Verify Variables Are Set

```python
from src.models.database import get_database

db = get_database()
with db.engine.connect() as conn:
    result = conn.execute(text("SELECT @aesKey, @customerIds, @serviceLocationIds"))
    aes_key, customer_ids, service_location_ids = result.fetchone()
    
    print(f"@aesKey: {'SET' if aes_key else 'NOT SET'}")
    print(f"@customerIds: {customer_ids}")
    print(f"@serviceLocationIds: {service_location_ids}")
```

Expected output:
```
@aesKey: SET
@customerIds: None
@serviceLocationIds: None
```

### Test Decryption

```python
# Query secure view
result = conn.execute(text("SELECT customerName FROM secure_customer LIMIT 1"))
name = result.fetchone()[0]

# Should be decrypted text, not binary blob
print(f"Customer name: {name}")  # "Acme Corp" (decrypted)
```

### Test Without Key

```python
# Temporarily unset
conn.execute(text("SET @aesKey = NULL"))

# Query should return NULL or encrypted blob
result = conn.execute(text("SELECT customerName FROM secure_customer LIMIT 1"))
name = result.fetchone()[0]

print(f"Customer name: {name}")  # NULL or <binary blob>
```

## Troubleshooting

### Views Return NULL

**Cause**: `@aesKey` not set or incorrect key
**Solution**: 
1. Check `.env` has `DB_ENCRYPT_KEY` set
2. Restart application to reload environment
3. Verify key matches the one used for encryption

### Performance Issues

**Cause**: Setting variables on every connection
**Solution**: 
- Connection pooling minimizes new connections
- Current pool size: 5 (sufficient for most workloads)
- Increase if needed: `pool_size=10, max_overflow=20`

### Security Concerns

**Cause**: Encryption key in environment variable
**Solutions**:
- Use AWS Secrets Manager / Azure Key Vault in production
- Rotate keys periodically
- Audit access to `.env` file
- Use separate keys per environment (dev/staging/prod)

## Security Best Practices

1. **Never log the encryption key**
   ```python
   logger.debug("Set @aesKey session variable")  # Good
   logger.debug(f"Set @aesKey = {key}")          # BAD!
   ```

2. **Use environment-specific keys**
   ```bash
   # Dev
   DB_ENCRYPT_KEY=dev_key_12345
   
   # Production  
   DB_ENCRYPT_KEY=prod_key_67890_complex
   ```

3. **Rotate keys regularly**
   - Plan: Quarterly rotation
   - Process: Encrypt with new key, update views, deprecate old key

4. **Limit key access**
   - Restrict `.env` file permissions: `chmod 600 .env`
   - Use secrets management in production
   - Never commit keys to git

## References

- [MySQL AES_ENCRYPT/AES_DECRYPT Documentation](https://dev.mysql.com/doc/refman/8.0/en/encryption-functions.html)
- [SQLAlchemy Event Listeners](https://docs.sqlalchemy.org/en/20/core/events.html)
- [MySQL Session Variables](https://dev.mysql.com/doc/refman/8.0/en/user-variables.html)
- Node.js Implementation: `api/controllers/smartReportController.js` (reference)
