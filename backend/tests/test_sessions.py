import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User
from app.repositories.user import UserRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_user(
    db_session: AsyncSession, email: str, password: str, is_active: bool = True
):
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": email,
            "password_hash": get_password_hash(password),
            "first_name": "Test",
            "last_name": "User",
            "is_active": is_active,
        }
    )


async def _login(client: AsyncClient, email: str, password: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"], data["session_id"]


@pytest.mark.asyncio(loop_scope="session")
async def test_login_returns_session_id(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "sess_login@example.com", "password")
    access_token, session_id = await _login(client, "sess_login@example.com", "password")
    assert session_id is not None
    assert len(session_id) > 0


@pytest.mark.asyncio(loop_scope="session")
async def test_list_sessions(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "sess_list@example.com", "password")
    access_token, session_id = await _login(client, "sess_list@example.com", "password")

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}", "X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == session_id


@pytest.mark.asyncio(loop_scope="session")
async def test_terminate_session(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "sess_term@example.com", "password")
    access_token, session_id = await _login(client, "sess_term@example.com", "password")

    response = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {access_token}", "X-Session-ID": session_id},
    )
    assert response.status_code == 204

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}", "X-Session-ID": session_id},
    )
    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_terminate_all_sessions(client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session, "sess_term_all@example.com", "password")
    access_token, session_id = await _login(
        client, "sess_term_all@example.com", "password"
    )

    response = await client.delete(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}", "X-Session-ID": session_id},
    )
    assert response.status_code == 204

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}", "X-Session-ID": session_id},
    )
    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_force_terminate_user_sessions(
    client: AsyncClient, db_session: AsyncSession
):
    result = await db_session.execute(
        select(Role).where(Role.name == "Admin", Role.org_id == DEFAULT_ORG_ID)
    )
    admin_role = result.scalar_one()
    guest_role = (
        await db_session.execute(
            select(Role).where(Role.name == "Guest", Role.org_id == DEFAULT_ORG_ID)
        )
    ).scalar_one()

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    admin = await repo.create(
        {
            "email": "sess_admin@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Admin",
            "last_name": "User",
            "role_id": admin_role.id,
        }
    )
    guest = await repo.create(
        {
            "email": "sess_guest@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Guest",
            "last_name": "User",
            "role_id": guest_role.id,
        }
    )

    admin_token, admin_session = await _login(client, "sess_admin@example.com", "password")
    guest_token, guest_session = await _login(client, "sess_guest@example.com", "password")

    response = await client.delete(
        f"/api/v1/admin/users/{guest.id}/sessions",
        headers={"Authorization": f"Bearer {admin_token}", "X-Session-ID": admin_session},
    )
    assert response.status_code == 204

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {guest_token}", "X-Session-ID": guest_session},
    )
    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_session_limit_for_admin(
    client: AsyncClient, db_session: AsyncSession
):
    result = await db_session.execute(
        select(Role).where(Role.name == "Admin", Role.org_id == DEFAULT_ORG_ID)
    )
    admin_role = result.scalar_one()

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    await repo.create(
        {
            "email": "sess_concurrent@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "Admin",
            "last_name": "User",
            "role_id": admin_role.id,
        }
    )

    for i in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "sess_concurrent@example.com", "password": "password"},
        )
        assert response.status_code == 200

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "sess_concurrent@example.com", "password": "password"},
    )
    assert response.status_code == 401
    assert "concurrent" in response.json()["detail"].lower()
