from app.prompt_engine.system_prompt import SYSTEM_PROMPT


def build_prompt(user_message: str, job_context: list) -> str:
    """
    Build prompt with clean, simple formatting
    """
    # Format jobs as clean numbered list
    if job_context:
        formatted_jobs = "\n\n".join([
            f"🔹 Công việc {idx}: {job['title']}\n"
            f"   • Công ty: {job['company']}\n"
            f"   • Địa điểm: {job['location']}\n"
            f"   • Lương: {job['salary']}\n"
            f"   • Kỹ năng: {job['skills']}\n"
            f"   • Mô tả: {job['description'][:150]}...\n"
            f"   • Yêu cầu: {job['requirements'][:150]}..."
            for idx, job in enumerate(job_context, 1)
        ])
        
        job_data_section = f"Tìm thấy {len(job_context)} công việc phù hợp:\n\n{formatted_jobs}"
    else:
        job_data_section = "Không tìm thấy công việc phù hợp."
    
    return f"""{SYSTEM_PROMPT}

===== DỮ LIỆU CÔNG VIỆC =====
{job_data_section}

===== CÂU HỎI =====
{user_message}

===== YÊU CẦU TRẢ LỜI =====
Hãy trả lời theo cấu trúc sau:

1. Giải thích tìm kiếm (1-2 câu):
   "Tôi tìm thấy [số lượng] công việc phù hợp vì [lý do khớp với yêu cầu của bạn]"

2. Danh sách công việc (top 3-5):
   Mỗi công việc gồm:
   - Tên công việc tại Công ty
   - Địa điểm, mức lương
   - Kỹ năng yêu cầu
   - Lý do phù hợp: Giải thích TẠI SAO công việc này khớp với câu hỏi

3. Lời khuyên (2-3 gợi ý):
   Đưa ra hướng dẫn cụ thể cho ứng viên

LƯU Ý QUAN TRỌNG:
- Luôn giải thích LÝ DO đề xuất mỗi công việc
- Không lặp lại nội dung
- Viết ngắn gọn, dễ hiểu"""
