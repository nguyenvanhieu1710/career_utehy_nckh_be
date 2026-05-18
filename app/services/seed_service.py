"""
Seed service for creating initial data
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.user import Users, UserRole, UserPerm
from app.models.perm_groups import PermGroups, GroupPermission
from app.models.cv_template import CVTemplate
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
                    "cv_template.create", "cv_template.read", "cv_template.update", "cv_template.delete"
                ]
                
                for perm in permissions:
                    group_perm = GroupPermission(
                        id=uuid.uuid4(),
                        group_id=admin_group.id,
                        perm=perm
                    )
                    db.add(group_perm)
            
            # Create admin user
            admin_password = "admin"
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


async def seed_cv_templates():
    """Create a default CV template if none exist"""
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(func.count()).select_from(CVTemplate))
            count = result.scalar()
            
            if count > 0:
                return

            # Basic default structure conforming to frontend Canvas expectations
            default_sections = """[
  {
    "id": "about",
    "title": "Giới thiệu",
    "open": true,
    "items": [
      {
        "text": "Viết vài dòng mô tả ngắn gọn về bản thân.",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 270,
    "y": 140,
    "size": { "width": 500, "height": 170 }
  },
  {
    "id": "contact",
    "title": "Thông tin liên hệ",
    "open": true,
    "items": [
      {
        "text": "email@example.com",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      },
      {
        "text": "0123 456 789",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      },
      {
        "text": "Thành phố, Quốc gia",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 20,
    "y": 310,
    "size": { "width": 200, "height": 200 }
  },
  {
    "id": "experience",
    "title": "Kinh nghiệm làm việc",
    "open": true,
    "items": [
      {
        "text": "Vị trí, tên công ty, thời gian làm việc.",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 270,
    "y": 310,
    "size": { "width": 500, "height": 400 }
  },
  {
    "id": "education",
    "title": "Học vấn",
    "open": true,
    "items": [
      {
        "text": "Tên trường, chuyên ngành, năm tốt nghiệp.",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 270,
    "y": 710,
    "size": { "width": 500, "height": 550 }
  },
  {
    "id": "language",
    "title": "Ngôn ngữ",
    "open": true,
    "items": [
      {
        "text": "Tiếng Anh – Trung cấp",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      },
      {
        "text": "Tiếng Việt – Bản ngữ",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 20,
    "y": 510,
    "size": { "width": 200, "height": 200 }
  },
  {
    "id": "skills",
    "title": "Kỹ năng",
    "open": true,
    "items": [
      {
        "text": "JavaScript, React, giao tiếp, làm việc nhóm",
        "editing": false,
        "tempText": "",
        "style": { "bold": false, "italic": false, "underline": false, "color": "#000000" },
        "children": [],
        "expanded": true
      }
    ],
    "adding": false,
    "editingIndex": null,
    "x": 20,
    "y": 710,
    "size": { "width": 200, "height": 200 }
  }
]"""
            design_data = '[{"id":"sidebar-bg","type":"rect","x":0,"y":0,"width":240,"height":1123,"fill":"#1d7057","zIndex":1}]'

            default_template = CVTemplate(
                id=uuid.uuid4(),
                name="Mẫu CV Cơ bản",
                category="Chung",
                is_active=True,
                default_title="Họ và Tên",
                default_subtitle="Vị trí ứng tuyển",
                primary_color="#1d7057ff",
                default_sections=default_sections,
                design_data=design_data
            )
            
            db.add(default_template)
            await db.commit()
            print("Default CV template seeded successfully.")
            
        except Exception as e:
            await db.rollback()
            print(f"Error seeding CV templates: {e}")


async def seed_initial_data():
    """Seed all initial data"""
    try:        
        # Create admin user
        await create_admin_user()
        
        # Seed default CV templates
        await seed_cv_templates()
                
    except Exception as e:
        raise e