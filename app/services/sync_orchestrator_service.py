import logging
import asyncio
import os
import aiohttp
from typing import List
from app.services.matching_proxy_service import MatchingProxyService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class SyncOrchestratorService:
    @staticmethod
    async def sync_matching_cluster(job_ids: List[str]):
        """Đồng bộ embeddings sang Matching Service"""
        try:
            payload = {"job_ids": job_ids}
            await MatchingProxyService._call_matching_api("/api/v1/admin/sync-jobs", json_data=payload, method="POST")
            logger.info(f"✅ [SyncOrchestrator] Đã đồng bộ embeddings cho {len(job_ids)} jobs mới (Matching Cluster).")
        except Exception as e:
            logger.error(f"❌ [SyncOrchestrator] Lỗi khi sync embeddings (Matching): {e}")
            
    @staticmethod
    async def sync_chatbot_cluster(job_ids: List[str]):
        """Đồng bộ embeddings sang Chatbot Service"""
        try:
            chatbot_url = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8001")
            api_url = f"{chatbot_url}/api/v1/chat/sync-new-jobs"
            payload = {"job_ids": job_ids}
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(api_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"✅ [SyncOrchestrator] Đã đồng bộ embeddings cho {len(job_ids)} jobs mới (Chatbot Cluster).")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ [SyncOrchestrator] Lỗi khi sync embeddings (Chatbot) - HTTP {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"❌ [SyncOrchestrator] Lỗi khi kết nối tới Chatbot Service để sync embeddings: {e}")

    @staticmethod
    async def handle_new_crawled_jobs(job_ids: List[str]):
        """
        Luồng điều phối chính khi có dữ liệu crawl mới:
        1. Đồng bộ đồng thời (parallel) sang cả Matching và Chatbot clusters.
        2. Kích hoạt NotificationService để quét và gửi email cho người dùng phù hợp.
        """
        if not job_ids:
            return

        logger.info(f"🚀 [SyncOrchestrator] Bắt đầu luồng xử lý cho {len(job_ids)} jobs mới.")

        # Chạy 2 task sync song song
        await asyncio.gather(
            SyncOrchestratorService.sync_matching_cluster(job_ids),
            SyncOrchestratorService.sync_chatbot_cluster(job_ids)
        )
        
        logger.info(f"✅ [SyncOrchestrator] Hoàn thành đồng bộ AI Models. Chuyển sang xử lý Notification.")
        
        # Gọi sang NotificationService
        await NotificationService.notify_suitable_users_on_new_jobs(job_ids)
