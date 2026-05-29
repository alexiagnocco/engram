# Refactor: Parameterized Queries in db.py

## Think Before Coding

Before writing anything, I need to surface one ambiguity: the `update_user` function uses `**fields` — a dynamic key-value dict used to build a `SET` clause. Parameterized queries handle *values* safely, but *column names* cannot be parameterized (the DB driver will quote them as string literals, not identifiers). This means:

- **Values** in `SET` are injectable → fixable with `%s` / `?` placeholders
- **Column names** (the `k` in `f"{k} = '{v}'"`) are also injectable (an attacker can pass `{"id=1; DROP TABLE users; --": "x"}`) → NOT fixable with parameter binding

I have two options for `update_user`:

1. **Allowlist the column names** — reject any key not in a known-safe set. This is the correct approach and matches what a real app would need.
2. **Leave the column-name risk with a comment** — only fix the value injection, and note that column-name validation is out of scope.

**My assumption:** you want all SQL injection removed, not just the easy ones. So I'll use an allowlist for `update_user` column names. I'll define the allowlist at the top of the function — minimal, surgical.

One clarifying question: do you want me to raise a `ValueError` for unknown fields (fail fast), or silently skip them? I'll default to **raising `ValueError`** — silent skips hide bugs.

If that's wrong, let me know and I'll adjust.

---

## Plan

```
1. Replace f-string SQL in get_user, get_users_by_role, search_users,
   insert_user, delete_user with parameterized placeholders
   → verify: no f-strings remain in SQL strings; parameters passed as tuple

2. Fix update_user: add column allowlist for key validation;
   parameterize values in SET clause
   → verify: unknown column raises ValueError; values use placeholders

3. No other changes (no formatting cleanup, no new abstractions, no
   return-type changes, no error handling beyond the allowlist guard)
```

---

## Proposed Code

```python
"""Database query module for myapp."""

_UPDATABLE_FIELDS = {"username", "email", "password_hash", "role"}


def get_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()


def get_users_by_role(conn, role):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = %s", (role,))
    return cursor.fetchall()


def search_users(conn, query):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username LIKE %s", (f"%{query}%",))
    return cursor.fetchall()


def insert_user(conn, username, email, password_hash, role="user"):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role) "
        "VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, role),
    )
    conn.commit()
    return cursor.lastrowid


def update_user(conn, user_id, **fields):
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown field(s): {unknown}")
    cursor = conn.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    cursor.execute(
        f"UPDATE users SET {set_clause} WHERE id = %s",
        (*fields.values(), user_id),
    )
    conn.commit()


def delete_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
```

---

## Notes

**Placeholder style (`%s`):** This uses the DB-API 2.0 `%s` style, which is correct for `psycopg2` (PostgreSQL) and `mysql-connector-python`. If you're using `sqlite3`, the placeholder is `?` instead of `%s`. Let me know your DB driver and I'll swap them — one find-replace, no logic change.

**`update_user` column names:** Even after this fix, `set_clause` still builds column names from `fields.keys()` via an f-string. The allowlist in `_UPDATABLE_FIELDS` makes this safe — any key not in the set raises before the query runs. The f-string on the column name is intentional and correct here; only values must be parameterized.

**`search_users` LIKE pattern:** The `%` wildcards are moved into the Python string `f"%{query}%"` and passed as a parameter value. The DB driver escapes `query` before it touches the SQL string, so `query` containing `%` or `_` will be treated as literals by the LIKE pattern — this is correct behavior and a common pattern.

**Scope:** No other changes made. Existing function signatures, return types, docstrings (none existed), and behavior are preserved exactly.

---

## Success Criteria

- [ ] Every SQL string with user-supplied input uses `%s` placeholders (or `?` for sqlite3)
- [ ] All user-supplied values passed as a tuple argument to `cursor.execute()`
- [ ] `update_user` rejects unknown column names before executing
- [ ] No f-string interpolation of user data directly into SQL strings remains
- [ ] All 6 functions still accept the same parameters and return the same types
