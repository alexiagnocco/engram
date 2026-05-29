"""Database query module for myapp."""


def get_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()


def get_users_by_role(conn, role):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE role = '{role}'")
    return cursor.fetchall()


def search_users(conn, query):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username LIKE '%{query}%'")
    return cursor.fetchall()


def insert_user(conn, username, email, password_hash, role="user"):
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO users (username, email, password_hash, role) "
        f"VALUES ('{username}', '{email}', '{password_hash}', '{role}')"
    )
    conn.commit()
    return cursor.lastrowid


def update_user(conn, user_id, **fields):
    cursor = conn.cursor()
    set_clause = ", ".join(f"{k} = '{v}'" for k, v in fields.items())
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id = {user_id}")
    conn.commit()


def delete_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM users WHERE id = {user_id}")
    conn.commit()
