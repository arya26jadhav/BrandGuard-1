
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg import Connection
from psycopg.rows import dict_row

from app.db import get_conn
from app.security import create_access_token, current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

USER_FIELDS = "id, name, initials, role, title, team"
ALLOWED_ROLES = ("creator", "manager", "reviewer", "admin")


class DemoLoginRequest(BaseModel):
    userId: str


def serialize_user(user: dict) -> dict:
    return {
        field: user[field]
        for field in ("id", "name", "initials", "role", "title", "team")
    }


@router.post("/demo-login")
def demo_login(
    payload: DemoLoginRequest,
    conn: Connection = Depends(get_conn),
):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
               f"SELECT {USER_FIELDS} FROM users WHERE id = %s AND is_demo_login = TRUE",
            (payload.userId,),
        )
        user = cur.fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="Unknown demo user")

    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        team=user["team"],
    )

    return {
        "token": token,
        "user": serialize_user(user),
    }


@router.get("/me")
def get_me(user: dict = Depends(current_user)):
    return serialize_user(user)


@router.get("/demo-users")
def get_demo_users(
    conn: Connection = Depends(get_conn),
):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {USER_FIELDS}
            FROM users
                       WHERE role IN (%s, %s, %s, %s) AND is_demo_login = TRUE
            ORDER BY name
            """,
            ALLOWED_ROLES,
        )
        users = cur.fetchall()

    return [serialize_user(user) for user in users]
