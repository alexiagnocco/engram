"""API handlers for myapp."""
import json


def handle_create_user(request_body):
    data = json.loads(request_body)
    username = data["username"]
    email = data["email"]
    password = data["password"]

    # TODO: add validation

    return {
        "status": 201,
        "body": {"id": 1, "username": username, "email": email},
    }


def handle_get_users(query_params):
    page = int(query_params.get("page", 1))
    limit = int(query_params.get("limit", 20))

    # Simulate DB query
    users = [
        {"id": i, "username": f"user_{i}", "email": f"user_{i}@example.com"}
        for i in range(1, 101)
    ]

    start = (page - 1) * limit
    end = start + limit

    return {
        "status": 200,
        "body": {"users": users[start:end], "total": len(users), "page": page},
    }


def handle_update_user(user_id, request_body):
    data = json.loads(request_body)
    return {
        "status": 200,
        "body": {"id": user_id, **data},
    }


def handle_delete_user(user_id):
    return {"status": 204, "body": None}


def fetch_data(url):
    import urllib.request

    try:
        response = urllib.request.urlopen(url)
        return json.loads(response.read())
    except Exception:
        return None


def fetch_with_retry(url, max_retries=3):
    """Fetch data from URL with basic retry."""
    import time

    for attempt in range(max_retries):
        result = fetch_data(url)
        if result is not None:
            return result
        time.sleep(1)
    return None
