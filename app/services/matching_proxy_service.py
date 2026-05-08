import os
import json
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.cv_profile import CVProfile

logger = logging.getLogger(__name__)

class MatchingProxyService:
    @staticmethod
    async def get_recommendations(cv_id: str, user_id: str, db: AsyncSession, top_k: int = 10, job_ids: List[str] = None):
        """
        Fetch recommendations from Matching Service for a given CV (JSON/Online)
        """
        # Fetch CV from database
        result = await db.execute(
            select(CVProfile).where(CVProfile.id == cv_id, CVProfile.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
        
        if not cv:
            raise HTTPException(status_code=404, detail="CV not found")

        sections_data = []
        if cv.sections:
            try:
                sections_data = json.loads(cv.sections) if isinstance(cv.sections, str) else cv.sections
            except json.JSONDecodeError:
                sections_data = []
        mapped_data = MatchingProxyService._map_sections_to_matching_input(cv, sections_data)
        
        return await MatchingProxyService._call_matching_api(
            "/api/v1/match/cv-json", 
            json_data=mapped_data, 
            params={"top_k": top_k, "job_ids": job_ids} if job_ids else {"top_k": top_k}
        )

    @staticmethod
    async def get_recommendations_from_file(cv_id: str, user_id: str, db: AsyncSession, top_k: int = 10, job_ids: List[str] = None):
        """
        Fetch recommendations using an uploaded PDF file
        """
        from app.models.cv_uploaded import CVUploaded
        result = await db.execute(
            select(CVUploaded).where(CVUploaded.id == cv_id, CVUploaded.user_id == user_id)
        )
        cv = result.scalar_one_or_none()
        
        if not cv or not cv.file_path:
            raise HTTPException(status_code=404, detail="Uploaded CV not found")

        # Normalize path: remove leading slash for joining correctly
        clean_path = cv.file_path.lstrip('/')
        file_path = os.path.join(os.getcwd(), clean_path)

        if not os.path.exists(file_path):
            # Fallback instead of 404: If file is missing, act as if no CV exists but log it
            logger.warning(f"CV File missing at: {file_path}. Falling back to recent jobs.")
            return {
                "success": True, 
                "matches": [], 
                "message": "CV file not found on server. Please re-upload.",
                "mode": "none"
            }

        matching_url = os.getenv("MATCHING_SERVICE_URL", "http://localhost:8002")
        # Ensure top_k and job_ids are sent as query parameters
        api_url = f"{matching_url}/api/v1/match/cv-file?top_k={top_k}"
        if job_ids:
            # aiohttp handles list of params by repeating the key
            for jid in job_ids:
                api_url += f"&job_ids={jid}"

        timeout = aiohttp.ClientTimeout(total=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path), content_type='application/pdf')

            try:
                async with session.post(api_url, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Matching service error {response.status}: {error_text}")
                        return {"success": False, "message": f"Matching service error: {response.status}"}
                    return await response.json()
            except Exception as e:
                logger.error(f"Error calling matching file API: {e}")
                return {"success": False, "message": str(e)}

    @staticmethod
    async def get_auto_recommendations(user_id: str, db: AsyncSession, top_k: int = 10, job_ids: List[str] = None):
        """
        Automatically detect the best CV to use for recommendations
        Scenario 4: Priority logic
        """
        # 1. Try Online CV (Profile) first
        from app.models.cv_profile import CVProfile
        profile_result = await db.execute(
            select(CVProfile).where(CVProfile.user_id == user_id).order_by(CVProfile.updated_at.desc())
        )
        cv_profile_item = profile_result.scalar_one_or_none()
        
        if cv_profile_item:
            logger.info(f"Auto-matching using Profile CV for user {user_id}")
            resp = await MatchingProxyService.get_recommendations(str(cv_profile_item.id), user_id, db, top_k, job_ids)
            if isinstance(resp, dict) and resp.get("mode") != "none":
                resp["mode"] = "profile"
            return resp

        # 2. Try Uploaded PDF if no Profile
        from app.models.cv_uploaded import CVUploaded
        uploaded_result = await db.execute(
            select(CVUploaded).where(CVUploaded.user_id == user_id).order_by(CVUploaded.updated_at.desc())
        )
        cv_uploaded_item = uploaded_result.scalar_one_or_none()
        
        if cv_uploaded_item:
            logger.info(f"Auto-matching using Uploaded PDF for user {user_id}")
            resp = await MatchingProxyService.get_recommendations_from_file(str(cv_uploaded_item.id), user_id, db, top_k)
            if isinstance(resp, dict) and resp.get("mode") != "none":
                resp["mode"] = "file"
            return resp

        # 3. Scenario 1: No CV at all
        logger.info(f"No CV found for user {user_id}, returning empty list (FE should handle fallback)")
        return {
            "success": True, 
            "matches": [], 
            "message": "No CV found. Please create or upload a CV for better recommendations.",
            "mode": "none"
        }

    @staticmethod
    async def _call_matching_api(endpoint: str, json_data: dict = None, params: dict = None, method: str = "POST"):
        matching_url = os.getenv("MATCHING_SERVICE_URL")
        api_url = f"{matching_url}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=600) # Increase timeout to 10 minutes
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # Use getattr to dynamically call method (post, get, etc.)
                http_method = getattr(session, method.lower())
                async with http_method(api_url, json=json_data, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Matching Service Error {response.status}: {error_text}")
                        return {"success": False, "message": f"Matching service error: {response.status}"}
                    return await response.json()
            except Exception as e:
                logger.error(f"Matching API call failed: {e}")
                return {"success": False, "message": str(e)}

    @staticmethod
    def _map_sections_to_matching_input(cv: CVProfile, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform CVProfile sections into CVJsonInput format for Matching Service
        """
        skills = []
        experience = []
        education = ""
        summary = f"{cv.title or ''} {cv.subtitle or ''}".strip()
        
        for section in sections:
            title = section.get("title", "").lower()
            items = section.get("items", [])
            
            # Extract text from complex item structure
            section_texts = []
            for item in items:
                text = item.get("text", "")
                if text:
                    section_texts.append(text)
                # Handle nested children if any
                for child in item.get("children", []):
                    if child.get("text"):
                        section_texts.append(child.get("text"))
            
            # Categorize based on keywords
            if any(kw in title for kw in ["kỹ năng", "skill"]):
                skills.extend(section_texts)
            elif any(kw in title for kw in ["kinh nghiệm", "experience", "làm việc"]):
                experience.extend(section_texts)
            elif any(kw in title for kw in ["học vấn", "education", "trường"]):
                education += "\n".join(section_texts)
            elif any(kw in title for kw in ["giới thiệu", "summary", "mục tiêu"]):
                summary += "\n" + "\n".join(section_texts)

        return {
            "name": cv.name,
            "skills": skills,
            "experience": "\n".join(experience),
            "education": education,
            "summary": summary.strip()
        }
