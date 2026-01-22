"""
Seed service for creating initial data
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import Users, UserRole, UserPerm
from app.models.perm_groups import PermGroups, GroupPermission
from app.core.database import SessionLocal
from app.services.user_service import hash_password
from app.core.status import EntityStatus

async def create_admin_user():
    """Create admin user with full permissions if not exists"""
    async with SessionLocal() as db:
        try:            
            # Check if admin user already exists
            result = await db.execute(
                select(Users).where(Users.email == "admin@gmail.com")
            )
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                return existing_admin
                        
            # Create Super Admin group if not exists
            result = await db.execute(
                select(PermGroups).where(PermGroups.name == "Admin")
            )
            admin_group = result.scalar_one_or_none()
            
            if not admin_group:
                admin_group = PermGroups(
                    id=uuid.uuid4(),
                    name="Admin",
                    description="Full system access"
                )
                db.add(admin_group)
                await db.flush()  # Get the ID
                
                # Add permissions to admin group
                permissions = [
                    "*",  # Wildcard for full access
                    "user.create", "user.read", "user.update", "user.delete", "user.list",
                    "role.create", "role.read", "role.update", "role.delete",
                    "job.create", "job.read", "job.update", "job.delete",
                    "company.create", "company.read", "company.update", "company.delete",
                    "category.create", "category.read", "category.update", "category.delete",
                ]
                
                for perm in permissions:
                    group_perm = GroupPermission(
                        id=uuid.uuid4(),
                        group_id=admin_group.id,
                        perm=perm
                    )
                    db.add(group_perm)
            
            # Create admin user
            admin_password = "123456"
            password_hash = hash_password(admin_password)
            
            admin_user = Users(
                id=uuid.uuid4(),
                email="admin@gmail.com",
                password_hash=password_hash,
                username="admin",
                fullname="Admin",
                action_status=EntityStatus.ACTIVE.value
            )
            db.add(admin_user)
            await db.flush()  # Get the ID
            
            # Assign admin user to admin group
            user_role = UserRole(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                group_id=admin_group.id
            )
            db.add(user_role)
            
            # Also add direct wildcard permission
            user_perm = UserPerm(
                id=uuid.uuid4(),
                user_id=admin_user.id,
                perm="*"
            )
            db.add(user_perm)
            
            await db.commit()

            
            return admin_user
            
        except Exception as e:
            await db.rollback()
            raise e


async def seed_initial_data():
    """Seed all initial data"""
    try:        
        # Create admin user
        await create_admin_user()
                
    except Exception as e:
        raise e