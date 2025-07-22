import resend
import logging
import os
from typing import Optional
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails using Resend API"""
    
    def __init__(self):
        self.api_key = "re_d7FZ5hf8_9NXHz4v3AnkMFGv6vCwdkbWS"
        
        # self.api_key = os.getenv('RESEND_API_KEY')
        if not self.api_key:
            logger.error("RESEND_API_KEY environment variable not set")
            raise ValueError("RESEND_API_KEY environment variable is required")
        
        resend.api_key = self.api_key
        self.db_service = DatabaseService()
        logger.info("EmailService initialized with Resend API")
    
    def send_feedback_ready_email(self, to_email: str, submission_uid: str) -> bool:
        """Send feedback ready notification email to user"""
        try:
            # Get user name from database
            submission = self.db_service.get_submission_by_url(submission_uid)
            user_name = "friend"  # Default fallback
            
            if submission and submission.get('student_id'):
                fetched_name = self.db_service.get_user_name_by_student_id(submission['student_id'])
                if fetched_name:
                    user_name = fetched_name
                    
            # Build the submission URL
            submission_url = f"https://app.nativespeaking.ai/student/submission/{submission_uid}/feedback"
            
            email_params = {
                "from": "Native Speaking Team <team@nativespeaking.ai>",
                "to": [to_email],
                "subject": "Your IELTS Speaking Assessment Report is Ready",
                "html": f"""
               <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Native Speaking - Assessment Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #282969; background-image: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 20px 20px; line-height: 1.6;">
    
    <!-- Main Container -->
    <div style="max-width: 680px; margin: 32px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.15);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #FF6B4A 0%, #EF5136 50%, #D4452C 100%); padding: 8px 0px; text-align: center; background: #fff;">
            <img src="https://media.licdn.com/dms/image/v2/D560BAQGNgpj7LgfmHA/company-logo_200_200/B56ZU7mddNGoAI-/0/1740461693298/nativespeaking_logo?e=1753920000&v=beta&t=wC7T5AjD411nBaCIerqPzIhoyMNdrDuMgHGJlkKeSNs" alt="Native Speaking Logo" style="height: 160px; width: auto; display: block; margin: 0 auto 16px auto; background: #fff; border-radius: 0; padding: 0;" />
        </div>

        <!-- Content -->
        <div style="padding: 48px 32px;">
            
            <!-- Greeting -->
            <div style="margin-bottom: 32px; text-align: left;">
                <h2 style="color: #1e293b; font-size: 24px; font-weight: 600; margin: 0 0 16px 0; line-height: 1.3;">
                    Yay, {user_name} đã nộp bài rồi nè 🎉
                </h2>
                <p style="color: #64748b; font-size: 16px; margin: 0;">
                    Hey hey <br><br>
                    👏 Một tràng pháo tay cho {user_name} vì đã hoàn thành bài tập!<br>
                    Bài của bạn đã được chấm điểm, và báo cáo chi tiết đã có mặt tại “trạm kết quả” rồi đây:
                </p>
            </div>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 40px 0;">
                <a href="{submission_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #FF6B4A 0%, #EF5136 50%, #D4452C 100%); color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(239, 81, 54, 0.3); transition: transform 0.2s ease;">
                    👉 Xem lại kết quả của bạn
                </a>
            </div>

            <!-- Additional Text -->
            <div style="margin-top: 24px;">
                <p style="color: #64748b; font-size: 15px; margin: 0 0 16px 0;">
                    Nếu bạn có thời gian, tụi mình khuyên nên luyện thêm 1-2 lần nữa cho bài này, càng luyện, càng “chém mượt” hơn nha 🔥
                </p>
                <p style="color: #64748b; font-size: 15px; margin: 0;">
                    Cần hỗ trợ gì thì cứ hú Native. Tụi mình ở đây để giúp bạn “nói đâu trúng đó”!
                </p>
            </div>

            <!-- Closing -->
            <div style="margin-top: 40px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                <p style="color: #64748b; font-size: 15px; margin: 0;">
                    Cheers,<br>
                    <strong style="color: #334155;">Đội ngũ Native Speaking</strong>
                </p>
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; padding: 32px; text-align: center; border-top: 1px solid #e2e8f0;">
            <div style="margin-bottom: 16px;">
                <a href="https://app.nativespeaking.ai" style="color: #EF5136; text-decoration: none; font-size: 14px; margin: 0 12px;">Website</a>
                <a href="https://app.nativespeaking.ai/legal/privacy-policy" style="color: #EF5136; text-decoration: none; font-size: 14px; margin: 0 12px;">Privacy</a>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin: 0;">© 2025 Native Speaking.</p>
        </div>
    </div>
</body>
</html>

                """
            }
            
            response = resend.Emails.send(email_params)
            logger.info(f"Email sent successfully to {to_email}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False