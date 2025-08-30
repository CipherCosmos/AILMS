from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from database import get_database, _uuid
from auth import _current_user
from models import (
    Permission, Role, Tenant, UserRole,
    StudentProfile, InstructorProfile, ParentGuardian,
    Department, CourseSection
)

rbac_router = APIRouter()

# System Roles Definition
SYSTEM_ROLES = {
    "super_admin": {
        "display_name": "Super Administrator",
        "description": "Platform-wide administrator with global access",
        "hierarchy_level": 100,
        "permissions": ["*"]  # All permissions
    },
    "org_admin": {
        "display_name": "Organization Administrator",
        "description": "Tenant administrator with full org control",
        "hierarchy_level": 90,
        "permissions": [
            "tenants:manage", "users:manage", "departments:manage",
            "courses:manage", "analytics:view", "billing:manage",
            "integrations:manage", "settings:manage"
        ]
    },
    "dept_admin": {
        "display_name": "Department Administrator",
        "description": "Department-level administrator",
        "hierarchy_level": 80,
        "permissions": [
            "departments:manage", "courses:create", "users:view",
            "analytics:view", "reports:generate"
        ]
    },
    "instructor": {
        "display_name": "Instructor",
        "description": "Course instructor with full course management",
        "hierarchy_level": 70,
        "permissions": [
            "courses:create", "courses:update", "courses:delete",
            "assignments:create", "assignments:grade", "students:view",
            "analytics:view", "discussions:moderate"
        ]
    },
    "teaching_assistant": {
        "display_name": "Teaching Assistant",
        "description": "Teaching assistant with limited grading rights",
        "hierarchy_level": 60,
        "permissions": [
            "assignments:grade", "students:view", "courses:view",
            "discussions:moderate", "submissions:view"
        ]
    },
    "content_author": {
        "display_name": "Content Author",
        "description": "Creates and manages learning content",
        "hierarchy_level": 50,
        "permissions": [
            "content:create", "content:update", "courses:view",
            "item_banks:manage", "files:upload"
        ]
    },
    "student": {
        "display_name": "Student",
        "description": "Learner with access to enrolled courses",
        "hierarchy_level": 20,
        "permissions": [
            "courses:view", "assignments:submit", "discussions:participate",
            "files:download", "progress:view"
        ]
    },
    "auditor": {
        "display_name": "Auditor",
        "description": "Read-only access for compliance and auditing",
        "hierarchy_level": 30,
        "permissions": [
            "courses:view", "analytics:view", "reports:view",
            "users:view", "content:view"
        ]
    },
    "parent_guardian": {
        "display_name": "Parent/Guardian",
        "description": "Access to child's progress and communications",
        "hierarchy_level": 15,
        "permissions": [
            "progress:view", "communications:view", "reports:view"
        ]
    },
    "proctor": {
        "display_name": "Proctor",
        "description": "Exam proctoring and integrity monitoring",
        "hierarchy_level": 40,
        "permissions": [
            "exams:monitor", "incidents:report", "recordings:view"
        ]
    },
    "support_moderator": {
        "display_name": "Support Moderator",
        "description": "Handles support tickets and content moderation",
        "hierarchy_level": 45,
        "permissions": [
            "tickets:manage", "content:moderate", "users:support",
            "reports:view", "analytics:view"
        ]
    },
    "career_coach": {
        "display_name": "Career Coach",
        "description": "Provides career guidance and mentoring",
        "hierarchy_level": 55,
        "permissions": [
            "career:advise", "mentoring:manage", "profiles:view",
            "opportunities:recommend"
        ]
    },
    "marketplace_manager": {
        "display_name": "Marketplace Manager",
        "description": "Manages course marketplace and monetization",
        "hierarchy_level": 75,
        "permissions": [
            "marketplace:manage", "courses:sell", "pricing:set",
            "reviews:moderate", "analytics:view"
        ]
    },
    "industry_reviewer": {
        "display_name": "Industry Reviewer",
        "description": "Industry expert for validating credentials",
        "hierarchy_level": 65,
        "permissions": [
            "credentials:review", "assessments:evaluate",
            "industry:validate", "reports:generate"
        ]
    },
    "alumni": {
        "display_name": "Alumni",
        "description": "Graduates with continued access",
        "hierarchy_level": 25,
        "permissions": [
            "content:view", "networking:access", "mentoring:participate",
            "opportunities:view"
        ]
    }
}


@rbac_router.post("/tenants")
async def create_tenant(tenant_data: dict, user=Depends(_current_user)):
    """Create a new tenant (Super Admin only)"""
    # Check if user is super admin
    db = get_database()
    user_doc = await db.users.find_one({"_id": user["id"]})
    if not user_doc or user_doc.get("role") != "super_admin":
        raise HTTPException(403, "Super Admin access required")

    tenant = Tenant(
        name=tenant_data["name"],
        domain=tenant_data.get("domain"),
        subdomain=tenant_data.get("subdomain"),
        branding=tenant_data.get("branding", {}),
        settings=tenant_data.get("settings", {}),
        plan=tenant_data.get("plan", "basic")
    )

    doc = tenant.dict()
    doc["_id"] = tenant.id
    await db.tenants.insert_one(doc)

    # Create default roles for the tenant
    await _create_tenant_roles(tenant.id)

    return tenant


@rbac_router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, user=Depends(_current_user)):
    """Get tenant information"""
    db = get_database()
    tenant = await db.tenants.find_one({"_id": tenant_id})
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # Check permissions
    user_doc = await db.users.find_one({"_id": user["id"]})
    if (user_doc.get("role") != "super_admin" and
        not await _has_tenant_access(user["id"], tenant_id)):
        raise HTTPException(403, "Access denied")

    return tenant


@rbac_router.get("/roles")
async def list_roles(tenant_id: Optional[str] = None, user=Depends(_current_user)):
    """List available roles"""
    db = get_database()

    if tenant_id:
        # Check tenant access
        if not await _has_tenant_access(user["id"], tenant_id):
            raise HTTPException(403, "Access denied")

    query = {"tenant_id": tenant_id} if tenant_id else {"is_system_role": True}
    roles = await db.roles.find(query).to_list(100)

    return [{"id": r["_id"], "name": r["name"], "display_name": r["display_name"],
             "description": r["description"]} for r in roles]


@rbac_router.post("/users/{user_id}/roles")
async def assign_role(user_id: str, role_data: dict, user=Depends(_current_user)):
    """Assign role to user"""
    db = get_database()

    # Check permissions
    if not await _can_manage_roles(user["id"], role_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    # Check if role exists
    role = await db.roles.find_one({"_id": role_data["role_id"]})
    if not role:
        raise HTTPException(404, "Role not found")

    user_role = UserRole(
        user_id=user_id,
        role_id=role_data["role_id"],
        tenant_id=role_data.get("tenant_id"),
        scope_id=role_data.get("scope_id"),
        scope_type=role_data.get("scope_type"),
        assigned_by=user["id"]
    )

    doc = user_role.dict()
    doc["_id"] = user_role.id
    await db.user_roles.insert_one(doc)

    return user_role


@rbac_router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role(user_id: str, role_id: str, user=Depends(_current_user)):
    """Remove role from user"""
    db = get_database()

    # Find the user role
    user_role = await db.user_roles.find_one({
        "user_id": user_id,
        "role_id": role_id
    })

    if not user_role:
        raise HTTPException(404, "Role assignment not found")

    # Check permissions
    if not await _can_manage_roles(user["id"], user_role.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    await db.user_roles.delete_one({"_id": user_role["_id"]})

    return {"status": "removed"}


@rbac_router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str, tenant_id: Optional[str] = None,
                              current_user=Depends(_current_user)):
    """Get effective permissions for a user"""
    db = get_database()

    # Check if current user can view permissions
    if (current_user["id"] != user_id and
        not await _can_manage_users(current_user["id"], tenant_id)):
        raise HTTPException(403, "Access denied")

    # Get all user roles
    query = {"user_id": user_id}
    if tenant_id:
        query["tenant_id"] = tenant_id

    user_roles = await db.user_roles.find(query).to_list(50)

    permissions = set()

    for user_role in user_roles:
        role = await db.roles.find_one({"_id": user_role["role_id"]})
        if role:
            permissions.update(role.get("permissions", []))

    return {
        "user_id": user_id,
        "permissions": list(permissions),
        "roles": [{"role_id": ur["role_id"], "scope": ur.get("scope_id")}
                 for ur in user_roles]
    }


@rbac_router.post("/departments")
async def create_department(dept_data: dict, user=Depends(_current_user)):
    """Create a new department"""
    db = get_database()

    # Check permissions
    if not await _can_manage_departments(user["id"], dept_data.get("tenant_id")):
        raise HTTPException(403, "Insufficient permissions")

    department = Department(
        tenant_id=dept_data["tenant_id"],
        name=dept_data["name"],
        code=dept_data["code"],
        parent_id=dept_data.get("parent_id"),
        head_id=dept_data.get("head_id"),
        description=dept_data.get("description")
    )

    doc = department.dict()
    doc["_id"] = department.id
    await db.departments.insert_one(doc)

    return department


@rbac_router.get("/departments")
async def list_departments(tenant_id: str, user=Depends(_current_user)):
    """List departments for a tenant"""
    db = get_database()

    if not await _has_tenant_access(user["id"], tenant_id):
        raise HTTPException(403, "Access denied")

    departments = await db.departments.find({"tenant_id": tenant_id}).to_list(100)
    return departments


@rbac_router.post("/users/{user_id}/profile/{profile_type}")
async def create_user_profile(user_id: str, profile_type: str, profile_data: dict,
                             user=Depends(_current_user)):
    """Create specialized profile for user"""
    db = get_database()

    # Check permissions
    if (user["id"] != user_id and
        not await _can_manage_users(user["id"], profile_data.get("tenant_id"))):
        raise HTTPException(403, "Access denied")

    profile_classes = {
        "student": StudentProfile,
        "instructor": InstructorProfile,
        "parent": ParentGuardian
    }

    if profile_type not in profile_classes:
        raise HTTPException(400, "Invalid profile type")

    profile_data["user_id"] = user_id
    profile = profile_classes[profile_type](**profile_data)

    collection_name = f"{profile_type}_profiles"
    doc = profile.dict()
    doc["_id"] = profile.id
    await db[collection_name].insert_one(doc)

    return profile


async def _create_tenant_roles(tenant_id: str):
    """Create default roles for a new tenant"""
    db = get_database()

    for role_name, role_data in SYSTEM_ROLES.items():
        if role_name != "super_admin":  # Super admin is global
            role = Role(
                name=role_name,
                display_name=role_data["display_name"],
                description=role_data["description"],
                tenant_id=tenant_id,
                permissions=role_data["permissions"],
                hierarchy_level=role_data["hierarchy_level"],
                is_system_role=True
            )

            doc = role.dict()
            doc["_id"] = role.id
            await db.roles.insert_one(doc)


async def _has_tenant_access(user_id: str, tenant_id: str) -> bool:
    """Check if user has access to tenant"""
    db = get_database()

    # Check if user has any role in the tenant
    user_role = await db.user_roles.find_one({
        "user_id": user_id,
        "tenant_id": tenant_id
    })

    if user_role:
        return True

    # Check if user is super admin
    user = await db.users.find_one({"_id": user_id})
    return user and user.get("role") == "super_admin"


async def _can_manage_roles(user_id: str, tenant_id: Optional[str] = None) -> bool:
    """Check if user can manage roles"""
    db = get_database()

    user = await db.users.find_one({"_id": user_id})
    if user and user.get("role") == "super_admin":
        return True

    if tenant_id:
        # Check for org_admin or dept_admin role in tenant
        user_role = await db.user_roles.find_one({
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role_id": {"$in": await _get_admin_role_ids(tenant_id)}
        })
        return user_role is not None

    return False


async def _can_manage_users(user_id: str, tenant_id: Optional[str] = None) -> bool:
    """Check if user can manage other users"""
    return await _can_manage_roles(user_id, tenant_id)


async def _can_manage_departments(user_id: str, tenant_id: str) -> bool:
    """Check if user can manage departments"""
    db = get_database()

    user = await db.users.find_one({"_id": user_id})
    if user and user.get("role") == "super_admin":
        return True

    # Check for org_admin role
    user_role = await db.user_roles.find_one({
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role_id": {"$in": await _get_admin_role_ids(tenant_id)}
    })

    return user_role is not None


async def _get_admin_role_ids(tenant_id: str) -> List[str]:
    """Get admin role IDs for a tenant"""
    db = get_database()

    admin_roles = await db.roles.find({
        "tenant_id": tenant_id,
        "name": {"$in": ["org_admin", "dept_admin"]}
    }).to_list(10)

    return [role["_id"] for role in admin_roles]


# Permission checking utility
async def check_permission(user_id: str, permission: str, tenant_id: Optional[str] = None,
                          scope_id: Optional[str] = None) -> bool:
    """Check if user has a specific permission"""
    db = get_database()

    # Get user roles
    query = {"user_id": user_id}
    if tenant_id:
        query["tenant_id"] = tenant_id
    if scope_id:
        query["scope_id"] = scope_id

    user_roles = await db.user_roles.find(query).to_list(50)

    for user_role in user_roles:
        role = await db.roles.find_one({"_id": user_role["role_id"]})
        if role and (permission in role.get("permissions", []) or "*" in role.get("permissions", [])):
            return True

    # Check global roles
    user = await db.users.find_one({"_id": user_id})
    if user and user.get("role") == "super_admin":
        return True

    return False