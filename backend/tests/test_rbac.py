import uuid

import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.security import get_password_hash
from app.main import app
from app.models.role import Role
from app.models.user import User
from app.repositories.user import UserRepository

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_test_router = APIRouter(prefix="/api/v1/test-rbac")


@_test_router.get("/any-role")
async def any_role_endpoint(user: User = Depends(get_current_user)):
    return {"user_id": str(user.id), "role": user.role.name if user.role else None}


@_test_router.get("/admin-only")
async def admin_only_endpoint(user: User = Depends(require_role(["Admin"]))):
    return {"user_id": str(user.id), "role": user.role.name}


@_test_router.get("/manager-or-admin")
async def manager_or_admin_endpoint(
    user: User = Depends(require_role(["Manager", "Admin"])),
):
    return {"user_id": str(user.id), "role": user.role.name}


app.include_router(_test_router)


async def _create_user_with_role(
    db_session: AsyncSession, email: str, password: str, role_name: str
) -> User:
    result = await db_session.execute(
        select(Role).where(Role.name == role_name, Role.org_id == DEFAULT_ORG_ID)
    )
    role = result.scalar_one_or_none()

    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    return await repo.create(
        {
            "email": email,
            "password_hash": get_password_hash(password),
            "first_name": "Test",
            "last_name": "User",
            "role_id": role.id if role else None,
        }
    )


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_get_current_user_valid_token(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user_with_role(
        db_session, "rbac_any@example.com", "password", "Guest"
    )
    token = await _login(client, "rbac_any@example.com", "password")

    response = await client.get(
        "/api/v1/test-rbac/any-role",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["role"] == "Guest"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/test-rbac/any-role",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_get_current_user_missing_token(client: AsyncClient):
    response = await client.get("/api/v1/test-rbac/any-role")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(client: AsyncClient, db_session: AsyncSession):
    user = await _create_user_with_role(
        db_session, "rbac_inactive@example.com", "password", "Guest"
    )
    # Deactivate user
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    await repo.update(user, {"is_active": False})

    from app.core.security import create_access_token

    fake_token = create_access_token(user.id, user.org_id)
    response = await client.get(
        "/api/v1/test-rbac/any-role",
        headers={"Authorization": f"Bearer {fake_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found or inactive"


@pytest.mark.asyncio
async def test_require_role_admin_allows_admin_blocks_others(
    client: AsyncClient, db_session: AsyncSession
):
    admin = await _create_user_with_role(
        db_session, "rbac_admin@example.com", "password", "Admin"
    )
    guest = await _create_user_with_role(
        db_session, "rbac_guest2@example.com", "password", "Guest"
    )

    admin_token = await _login(client, "rbac_admin@example.com", "password")
    guest_token = await _login(client, "rbac_guest2@example.com", "password")

    response = await client.get(
        "/api/v1/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "Admin"

    response = await client.get(
        "/api/v1/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_require_role_user_without_role(client: AsyncClient, db_session: AsyncSession):
    repo = UserRepository(db_session, DEFAULT_ORG_ID)
    user = await repo.create(
        {
            "email": "rbac_norole@example.com",
            "password_hash": get_password_hash("password"),
            "first_name": "No",
            "last_name": "Role",
        }
    )

    token = await _login(client, "rbac_norole@example.com", "password")

    response = await client.get(
        "/api/v1/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User has no assigned role"


@pytest.mark.asyncio
async def test_require_role_all_five_roles(client: AsyncClient, db_session: AsyncSession):
    roles = ["Admin", "Owner", "Manager", "Partner", "Guest"]

    tokens = {}
    for role_name in roles:
        email = f"rbac_{role_name.lower()}@example.com"
        await _create_user_with_role(db_session, email, "password", role_name)
        tokens[role_name] = await _login(client, email, "password")

    # Test manager-or-admin endpoint
    allowed_for_manager_admin = {"Manager", "Admin"}
    for role_name in roles:
        response = await client.get(
            "/api/v1/test-rbac/manager-or-admin",
            headers={"Authorization": f"Bearer {tokens[role_name]}"},
        )
        if role_name in allowed_for_manager_admin:
            assert response.status_code == 200, f"{role_name} should access manager-or-admin"
            assert response.json()["role"] == role_name
        else:
            assert response.status_code == 403, f"{role_name} should NOT access manager-or-admin"

    # Test admin-only endpoint
    for role_name in roles:
        response = await client.get(
            "/api/v1/test-rbac/admin-only",
            headers={"Authorization": f"Bearer {tokens[role_name]}"},
        )
        if role_name == "Admin":
            assert response.status_code == 200, f"{role_name} should access admin-only"
        else:
            assert response.status_code == 403, f"{role_name} should NOT access admin-only"
