import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import Users
from app.models.cv_profile import CVProfile
from app.models.cv_uploaded import CVUploaded
from app.services.matching_proxy_service import MatchingProxyService
from app.api.v1.email import FastMail, MessageSchema, ConnectionConfig, generate_email_html, email_conf
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def notify_suitable_users_on_new_jobs(job_ids: List[str]):
        """
        Gửi thông báo cho các người dùng phù hợp với danh sách job mới.
        Quy trình: 
        1. (Đã được xử lý ở SyncOrchestrator) Đồng bộ AI Models.
        2. Tìm các user có CV.
        3. Với mỗi user, lấy top recommendations và check xem có job mới nào trong đó không.
        4. Gửi mail nếu tìm thấy job phù hợp.
        """
        if not job_ids:
            return

        logger.info(f"🔔 [Notification] Bắt đầu xử lý thông báo cho {len(job_ids)} jobs mới.")


        async with SessionLocal() as db:
            # Bước 2: Tìm tất cả người dùng active có ít nhất 1 CV (Online hoặc Uploaded)
            stmt = select(Users).where(
                (Users.id.in_(select(CVProfile.user_id))) | 
                (Users.id.in_(select(CVUploaded.user_id)))
            )
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            logger.info(f"🔍 [Notification] Đang kiểm tra gợi ý cho {len(users)} người dùng...")
            
            for user in users:
                try:
                    # Bước 3: Lấy gợi ý tự động cho User (Chỉ so khớp với đúng danh sách job mới)
                    recommendations = await MatchingProxyService.get_auto_recommendations(str(user.id), db, top_k=10, job_ids=job_ids)
                    
                    if not recommendations.get("success") or not recommendations.get("matches"):
                        logger.info(f"ℹ️ [Notification] AI không tìm thấy gợi ý nào phù hợp cho user {user.email}")
                        continue
                        
                    logger.info(f"📊 [Notification] AI trả về {len(recommendations['matches'])} gợi ý cho user {user.email}")

                    # Lọc ra các job mới nằm trong danh sách gợi ý và có điểm > 70% (Production)
                    suitable_new_jobs = []
                    # Đảm bảo job_ids là list string để so sánh
                    str_job_ids = [str(jid) for jid in job_ids]

                    for match in recommendations["matches"]:
                        # Ép kiểu ID từ AI sang string
                        match_job_id = str(match["job_id"])
                        score = match.get("compatibility_score", 0)
                        
                        if match_job_id in str_job_ids and score >= 70:
                            suitable_new_jobs.append({
                                "title": match["job_title"],
                                "company": match["company"],
                                "score": score,
                                "location": match.get("location", "N/A")
                            })
                    
                    # Bước 4: Gửi Email nếu có job phù hợp
                    if suitable_new_jobs:
                        logger.info(f"📧 [Notification] Tìm thấy {len(suitable_new_jobs)} job mới phù hợp cho {user.email}. Bắt đầu gửi mail...")
                        await NotificationService.send_recommendation_email(user, suitable_new_jobs)
                    else:
                        logger.info(f"ℹ️ [Notification] Không có job mới nào trong {len(job_ids)} job vừa crawl phù hợp với user {user.email} (ngưỡng 10%)")
                        
                    # Tránh làm nghẽn SMTP server
                    await asyncio.sleep(0.5) 
                    
                except Exception as e:
                    logger.error(f"❌ [Notification] Lỗi khi xử lý thông báo cho user {user.email}: {e}")

    @staticmethod
    async def send_recommendation_email(user: Users, jobs: List[Dict[str, Any]]):
        """
        Gửi email gợi ý việc làm.
        """
        try:
            html = generate_email_html("job_recommendation", jobs)
            
            message = MessageSchema(
                subject="CAREER - Gợi ý việc làm mới phù hợp với bạn",
                recipients=[user.email],
                body=html,
                subtype="html"
            )
            
            fm = FastMail(email_conf)
            await fm.send_message(message)
            logger.info(f"✅ [Notification] Đã gửi email thành công tới {user.email}")
        except Exception as e:
            logger.error(f"❌ [Notification] Lỗi gửi mail tới {user.email}: {e}")
