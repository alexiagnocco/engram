# Refactoring db.py to Use Parameterized Queries

I've reviewed the file. Every function uses Python f-strings to interpolate user-supplied values directly into SQL strings — that's a textbook SQL injection surface. Here's a breakdown of each vulnerability and the fix.

## Vulnerabilities Found

| Function | Issue |
|---|---|
| `get_user` | `user_id` interpolated as integer — type confusion attack possible |
| `get_users_by_role` | `role` string interpolated without quoting escape — classic `' OR '1'='1` |
| `search_users` | `query` inside `LIKE '%...%'` — wildcard injection + comment bypass |
| `insert_user` | All four string fields unescaped — data exfiltration or second-order injection |
| `update_user` | Dynamic `SET` clause built from `**fields` — attacker controls column names AND values |
| `delete_user` | `user_id` interpolated — same as `get_user` |

The `update_user` function has a second issue beyond injection: it accepts arbitrary keyword arguments and builds a `SET` clause directly from them. That means a caller can pass any column name as a key, including ones that shouldn't be user-writable (e.g., `password_hash`, `role`, `id`). The fix below adds a column allowlist.

## Refactored db.py

```python
"""Database query module for myapp."""

# Columns callers are permitted to update via update_user().
# Expanding this set is a conscious security decision.
_UPDATABLE_COLUMNS = frozenset({"username", "email", "password_hash", "role"})


def get_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def get_users_by_role(conn, role):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = ?", (role,))
    return cursor.fetchall()


def search_users(conn, query):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username LIKE ?", (f"%{query}%",))
    return cursor.fetchall()


def insert_user(conn, username, email, password_hash, role="user"):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role) "
        "VALUES (?, ?, ?, ?)",
        (username, email, password_hash, role),
    )
    conn.commit()
    return cursor.lastrowid


def update_user(conn, user_id, **fields):
    if not fields:
        return

    unknown = set(fields) - _UPDATABLE_COLUMNS
    if unknown:
        raise ValueError(f"update_user: disallowed column(s): {unknown}")

    cursor = conn.cursor()
    # Column names come from the allowlist above, so they are safe to
    # interpolate into the SET clause. Values are still bound as parameters.
    set_clause = ", ".join(f"{col} = ?" for col in fields)
    params = list(fields.values()) + [user_id]
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", params)
    conn.commit()


def delete_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
```

## Key Changes Explained

**`?` placeholders (SQLite DB-API 2.0 style)**
All user-supplied values are passed as the second argument to `cursor.execute()` — a tuple of bind parameters. The database driver handles escaping; the application never touches quoting.

If you're using PostgreSQL via `psycopg2`, swap `?` for `%s`. If you're using MySQL via `mysql-connector-python`, `?` works as-is. The pattern is identical; only the placeholder character differs.

**`search_users` — LIKE wildcard placement**
The `%` wildcards are part of the *value*, not the SQL structure, so they belong in the Python string that gets bound: `f"%{query}%"`. The SQL itself just has `LIKE ?`. This is correct and safe — the driver escapes the bound value including any `%` or `_` characters in `query` that would otherwise be interpreted as LIKE wildcards.

> One nuance: if `query` itself contains `%` or `_` and you want those treated as literals (not SQL wildcards), you need to escape them before binding: `query.replace("%", r"\%").replace("_", r"\_")` and add `ESCAPE '\'` to the SQL. Whether you need this depends on your product requirements.

**`update_user` — column allowlist**
Column names can't be parameterized (only *values* can be). The original code accepted arbitrary `**fields` keys and interpolated them directly — an attacker who controls keyword argument names could inject arbitrary SQL into the `SET` clause. The fix:
1. Validates every key against `_UPDATABLE_COLUMNS` before building the query.
2. Raises `ValueError` on unknown columns so bugs are loud, not silent.
3. Still binds all *values* as parameters.

**Empty `fields` guard**
If `update_user` is called with no keyword arguments, the old code would have executed `UPDATE users SET  WHERE id = ...` (syntax error). The guard returns early instead.

## No Behavior Changes

All public signatures are unchanged. Return values, `conn.commit()` placement, and `cursor.lastrowid` usage are identical. This is a pure security fix with no observable behavior difference for valid inputs.
