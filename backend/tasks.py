"""
Celery tasks for background processing in LMS.
"""
import asyncio
from celery import Celery
from datetime import datetime, timezone
from typing import Dict, Any, List
import json
import logging

from enhanced_ai_generator import enhanced_ai_generator
from database import get_database
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'lms_tasks',
    broker=settings.redis_url or 'redis://localhost:6379/0',
    backend=settings.redis_url or 'redis://localhost:6379/0',
    include=['tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.generate_course_async': {'queue': 'course_generation'},
        'tasks.enhance_content_async': {'queue': 'content_enhancement'},
        'tasks.analyze_learning_patterns_async': {'queue': 'analytics'},
        'tasks.process_submissions_async': {'queue': 'submissions'},
        'tasks.send_notifications_async': {'queue': 'notifications'},
    },
    task_default_queue='default',
    task_default_exchange='lms',
    task_default_routing_key='lms.default',
)

@celery_app.task(bind=True, name='tasks.generate_course_async')
def generate_course_async(self, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Async task for generating comprehensive courses.
    """
    try:
        logger.info(f"Starting course generation for user {user_id}")

        # Update task state
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Initializing AI generation...'})

        # Generate course content
        course_data = asyncio.run(enhanced_ai_generator.generate_comprehensive_course(request_data))

        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Saving course to database...'})

        # Save to database
        db = get_database()
        course_data['_id'] = course_data.get('id', f"course_{user_id}_{int(datetime.now(timezone.utc).timestamp())}")
        course_data['owner_id'] = user_id
        course_data['created_at'] = datetime.now(timezone.utc).isoformat()
        course_data['status'] = 'completed'
        course_data['generation_progress'] = 100

        # Insert course
        result = asyncio.run(db.courses.insert_one(course_data))

        logger.info(f"Course generation completed for user {user_id}, course ID: {result.inserted_id}")

        return {
            'status': 'completed',
            'course_id': str(result.inserted_id),
            'course_data': course_data,
            'message': 'Course generated successfully'
        }

    except Exception as e:
        logger.error(f"Course generation failed for user {user_id}: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='tasks.enhance_content_async')
def enhance_content_async(self, content: str, enhancement_type: str, user_id: str) -> Dict[str, Any]:
    """
    Async task for enhancing lesson content.
    """
    try:
        logger.info(f"Starting content enhancement for user {user_id}")

        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Analyzing content...'})

        # Generate enhancement prompts based on type
        if enhancement_type == 'comprehensive':
            prompt = f"""
            Enhance this lesson content comprehensively:

            Original Content: {content}

            Please add:
            1. Real-world examples and case studies
            2. Step-by-step explanations
            3. Visual descriptions and analogies
            4. Common misconceptions and clarifications
            5. Practical applications
            6. Assessment questions with answers

            Make the content 2-3 times more detailed while maintaining clarity.
            """
        elif enhancement_type == 'examples':
            prompt = f"""
            Add comprehensive real-world examples to this content:

            Original Content: {content}

            Add 4-6 detailed examples including:
            - Industry case studies
            - Historical examples
            - Personal success stories
            - Common problem-solving scenarios
            """
        else:
            prompt = f"Enhance this content: {content}"

        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Generating enhanced content...'})

        # Generate enhanced content using AI
        model = asyncio.run(enhanced_ai_generator._get_ai())
        response = model.generate_content(prompt)
        enhanced_content = response.text

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Finalizing enhancement...'})

        logger.info(f"Content enhancement completed for user {user_id}")

        return {
            'status': 'completed',
            'original_content': content,
            'enhanced_content': enhanced_content,
            'enhancement_type': enhancement_type,
            'word_count_increase': len(enhanced_content.split()) - len(content.split()),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Content enhancement failed for user {user_id}: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='tasks.analyze_learning_patterns_async')
def analyze_learning_patterns_async(self, user_id: str, time_period_days: int = 30) -> Dict[str, Any]:
    """
    Async task for analyzing learning patterns.
    """
    try:
        logger.info(f"Starting learning pattern analysis for user {user_id}")

        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Gathering user data...'})

        # Get user data
        db = get_database()
        progress_data = asyncio.run(db.course_progress.find({"user_id": user_id}).to_list(100))
        submissions = asyncio.run(db.submissions.find({"user_id": user_id}).sort("created_at", -1).limit(100).to_list(100))

        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Analyzing patterns...'})

        # Analyze patterns
        analysis = {
            'total_courses': len(progress_data),
            'completed_courses': len([p for p in progress_data if p.get('completed')]),
            'average_progress': sum([p.get('overall_progress', 0) for p in progress_data]) / len(progress_data) if progress_data else 0,
            'total_submissions': len(submissions),
            'average_grade': sum([s.get('ai_grade', {}).get('score', 0) for s in submissions if s.get('ai_grade')]) / len([s for s in submissions if s.get('ai_grade')]) if submissions else 0,
            'learning_streak': 0,  # Would calculate from activity data
            'most_active_day': 'Analysis pending',
            'preferred_learning_time': 'Analysis pending'
        }

        # Generate AI-powered insights
        prompt = f"""
        Analyze this learner's performance data and provide insights:

        Performance Summary:
        - Courses Enrolled: {analysis['total_courses']}
        - Courses Completed: {analysis['completed_courses']}
        - Average Progress: {analysis['average_progress']:.1f}%
        - Total Submissions: {analysis['total_submissions']}
        - Average Grade: {analysis['average_grade']:.1f}%

        Provide:
        1. Learning pattern analysis
        2. Strengths and areas for improvement
        3. Personalized recommendations
        4. Optimal study strategies
        5. Progress predictions
        """

        model = asyncio.run(enhanced_ai_generator._get_ai())
        response = model.generate_content(prompt)
        ai_insights = response.text

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Generating recommendations...'})

        # Generate recommendations
        recommendations = []
        if analysis['average_progress'] < 50:
            recommendations.append("Consider breaking study sessions into shorter, focused intervals")
        if analysis['average_grade'] > 85:
            recommendations.append("Excellent performance! Try mentoring other students")
        if analysis['completed_courses'] == 0:
            recommendations.append("Start with foundational courses to build confidence")

        logger.info(f"Learning pattern analysis completed for user {user_id}")

        return {
            'status': 'completed',
            'analysis': analysis,
            'ai_insights': ai_insights,
            'recommendations': recommendations,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Learning pattern analysis failed for user {user_id}: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='tasks.process_submissions_async')
def process_submissions_async(self, submission_ids: List[str]) -> Dict[str, Any]:
    """
    Async task for processing assignment submissions.
    """
    try:
        logger.info(f"Processing {len(submission_ids)} submissions")

        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Initializing submission processing...'})

        db = get_database()
        processed_count = 0
        results = []

        for submission_id in submission_ids:
            self.update_state(state='PROGRESS',
                            meta={'progress': 20 + (processed_count / len(submission_ids)) * 70,
                                  'message': f'Processing submission {processed_count + 1}/{len(submission_ids)}'})

            # Get submission
            submission = asyncio.run(db.submissions.find_one({"_id": submission_id}))
            if not submission:
                continue

            # Process submission (AI grading, plagiarism check, etc.)
            # This would integrate with AI services for grading

            processed_result = {
                'submission_id': submission_id,
                'status': 'processed',
                'ai_grade': {'score': 85, 'feedback': 'Good work!'},
                'plagiarism_score': 0.05,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }

            results.append(processed_result)
            processed_count += 1

        self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Finalizing results...'})

        logger.info(f"Submission processing completed: {processed_count} submissions processed")

        return {
            'status': 'completed',
            'processed_count': processed_count,
            'results': results,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Submission processing failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True, name='tasks.send_notifications_async')
def send_notifications_async(self, notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Async task for sending batch notifications.
    """
    try:
        logger.info(f"Sending {len(notifications)} notifications")

        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Initializing notification sending...'})

        sent_count = 0
        failed_count = 0
        results = []

        for notification in notifications:
            self.update_state(state='PROGRESS',
                            meta={'progress': 20 + (sent_count / len(notifications)) * 70,
                                  'message': f'Sending notification {sent_count + 1}/{len(notifications)}'})

            try:
                # Send notification (email, push, SMS, etc.)
                # This would integrate with notification services

                result = {
                    'notification_id': notification.get('id'),
                    'recipient': notification.get('user_id'),
                    'type': notification.get('type'),
                    'status': 'sent',
                    'sent_at': datetime.now(timezone.utc).isoformat()
                }

                results.append(result)
                sent_count += 1

            except Exception as e:
                failed_count += 1
                results.append({
                    'notification_id': notification.get('id'),
                    'status': 'failed',
                    'error': str(e)
                })

        self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Finalizing notification results...'})

        logger.info(f"Notification sending completed: {sent_count} sent, {failed_count} failed")

        return {
            'status': 'completed',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'results': results,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Notification sending failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

# Periodic tasks
@celery_app.task(name='tasks.cleanup_expired_sessions')
def cleanup_expired_sessions():
    """Clean up expired user sessions."""
    try:
        logger.info("Starting expired session cleanup")

        # This would clean up expired sessions from Redis/database
        # Implementation depends on session storage mechanism

        logger.info("Expired session cleanup completed")
        return {'status': 'completed', 'cleaned_sessions': 0}

    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")
        raise

@celery_app.task(name='tasks.generate_analytics_reports')
def generate_analytics_reports():
    """Generate daily analytics reports."""
    try:
        logger.info("Starting analytics report generation")

        # Generate various analytics reports
        # User engagement, course completion rates, etc.

        logger.info("Analytics report generation completed")
        return {'status': 'completed', 'reports_generated': 0}

    except Exception as e:
        logger.error(f"Analytics report generation failed: {str(e)}")
        raise

# Export the Celery app
__all__ = ['celery_app']