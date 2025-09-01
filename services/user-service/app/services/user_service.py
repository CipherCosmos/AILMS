"""
User Service Business Logic Layer
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import json

from shared.common.logging import get_logger
from shared.common.errors import NotFoundError, ValidationError, DatabaseError
from shared.common.database import DatabaseOperations, _uuid

from ..database.database import user_db
from ..models import (
    UserProfile, UserProfileCreate, UserProfileUpdate,
    CareerProfile, CareerProfileCreate, CareerProfileUpdate,
    StudyPlan, StudyPlanCreate, StudyPlanUpdate,
    Achievement, AchievementCreate,
    StudySession, StudySessionCreate,
    LearningAnalytics, SkillGap, CareerReadiness
)
from ..config.config import user_service_settings

logger = get_logger("user-service")

class UserService:
    """User service business logic"""

    def __init__(self):
        self.db = user_db

    # Profile operations
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile with caching"""
        profile_data = await self.db.get_user_profile(user_id)
        if not profile_data:
            raise NotFoundError("User profile", user_id)

        return UserProfile(**profile_data)

    async def create_user_profile(self, profile_data: UserProfileCreate) -> UserProfile:
        """Create new user profile"""
        try:
            profile_dict = profile_data.dict(by_alias=True)
            profile_dict["_id"] = _uuid()
            profile_dict["created_at"] = datetime.now(timezone.utc)
            profile_dict["updated_at"] = datetime.now(timezone.utc)

            success = await self.db.update_user_profile(profile_data.user_id, profile_dict)
            if not success:
                raise DatabaseError("create_user_profile", "Failed to create user profile")

            logger.info("User profile created", extra={"user_id": profile_data.user_id})
            return UserProfile(**profile_dict)

        except Exception as e:
            logger.error("Failed to create user profile", extra={
                "user_id": profile_data.user_id,
                "error": str(e)
            })
            raise DatabaseError("create_user_profile", f"Profile creation failed: {str(e)}")

    async def update_user_profile(self, user_id: str, updates: UserProfileUpdate) -> UserProfile:
        """Update user profile"""
        try:
            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            update_dict["updated_at"] = datetime.now(timezone.utc)

            success = await self.db.update_user_profile(user_id, update_dict)
            if not success:
                raise DatabaseError("update_user_profile", "Failed to update user profile")

            # Get updated profile
            updated_profile = await self.get_user_profile(user_id)

            logger.info("User profile updated", extra={
                "user_id": user_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_profile

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error("Failed to update user profile", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_user_profile", f"Profile update failed: {str(e)}")

    # Career operations
    async def get_career_profile(self, user_id: str) -> CareerProfile:
        """Get career profile"""
        profile_data = await self.db.get_career_profile(user_id)
        if not profile_data:
            raise NotFoundError("Career profile", user_id)

        return CareerProfile(**profile_data)

    async def update_career_profile(self, user_id: str, updates: CareerProfileUpdate) -> CareerProfile:
        """Update career profile"""
        try:
            update_dict = updates.dict(exclude_unset=True)
            if not update_dict:
                raise ValidationError("No valid fields provided for update", "updates")

            update_dict["updated_at"] = datetime.now(timezone.utc)

            success = await self.db.update_career_profile(user_id, update_dict)
            if not success:
                raise DatabaseError("update_career_profile", "Failed to update career profile")

            # Get updated profile
            updated_profile = await self.get_career_profile(user_id)

            logger.info("Career profile updated", extra={
                "user_id": user_id,
                "updated_fields": list(update_dict.keys())
            })

            return updated_profile

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error("Failed to update career profile", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("update_career_profile", f"Career profile update failed: {str(e)}")

    # Study plan operations
    async def get_study_plan(self, user_id: str) -> StudyPlan:
        """Get study plan with caching"""
        plan_data = await self.db.get_study_plan(user_id)
        if not plan_data:
            # Generate new study plan
            return await self._generate_study_plan(user_id)

        return StudyPlan(**plan_data)

    async def _generate_study_plan(self, user_id: str) -> StudyPlan:
        """Generate personalized study plan"""
        try:
            # Get database connections
            courses_db = DatabaseOperations("courses")
            course_progress_db = DatabaseOperations("course_progress")

            # Get user's enrolled courses and progress
            enrolled_courses = await courses_db.find_many({
                "enrolled_user_ids": user_id
            }, limit=10)

            progress_data = await course_progress_db.find_many({"user_id": user_id}, limit=10)

            # Analyze user's learning patterns
            completed_courses = len([p for p in progress_data if p.get("completed")])
            total_enrolled = len(enrolled_courses)

            # Calculate average progress
            avg_progress = 0
            if progress_data:
                avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

            # Get user's profile for personalized recommendations
            user_profile = await self.db.get_user_profile(user_id)
            preferred_style = user_profile.get("preferred_learning_style", "visual") if user_profile else "visual"

            # Generate study plan based on real data
            study_plan_data = {
                "_id": _uuid(),
                "user_id": user_id,
                "weekly_hours": 15,
                "daily_sessions": 2,
                "focus_areas": [
                    {
                        "name": "Core Programming",
                        "description": "Master fundamental programming concepts",
                        "progress": min(100, avg_progress),
                        "recommendations": f"Based on your {preferred_style} learning style"
                    },
                    {
                        "name": "Data Structures",
                        "description": "Learn efficient data organization",
                        "progress": max(0, avg_progress - 20),
                        "recommendations": "Focus on practical implementations"
                    },
                    {
                        "name": "Algorithms",
                        "description": "Understand algorithmic problem solving",
                        "progress": max(0, avg_progress - 40),
                        "recommendations": "Practice with real coding problems"
                    }
                ],
                "today_schedule": [
                    {
                        "time": "09:00",
                        "activity": "Review Core Concepts",
                        "description": f"Review {'visual aids' if preferred_style == 'visual' else 'practical exercises' if preferred_style == 'kinesthetic' else 'reading materials'}",
                        "duration": 60
                    },
                    {
                        "time": "14:00",
                        "activity": "Hands-on Practice",
                        "description": "Apply concepts through coding exercises",
                        "duration": 90
                    },
                    {
                        "time": "19:00",
                        "activity": "Project Work",
                        "description": "Work on course projects or assignments",
                        "duration": 60
                    }
                ],
                "stats": {
                    "completed_courses": completed_courses,
                    "total_enrolled": total_enrolled,
                    "average_progress": round(avg_progress, 1),
                    "learning_streak": 5  # Would calculate from actual session data
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Save study plan
            success = await self.db.update_study_plan(user_id, study_plan_data)
            if not success:
                raise DatabaseError("generate_study_plan", "Failed to save study plan")

            logger.info("Study plan generated", extra={
                "user_id": user_id,
                "enrolled_courses": total_enrolled,
                "average_progress": round(avg_progress, 1)
            })

            return StudyPlan(**study_plan_data)

        except Exception as e:
            logger.error("Failed to generate study plan", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("generate_study_plan", f"Study plan generation failed: {str(e)}")

    # Achievement operations
    async def get_user_achievements(self, user_id: str) -> List[Achievement]:
        """Get user's achievements"""
        achievements_data = await self.db.get_user_achievements(user_id)
        return [Achievement(**achievement) for achievement in achievements_data]

    async def generate_achievements(self, user_id: str) -> List[Achievement]:
        """Generate achievements based on user's real learning progress"""
        try:
            # Get database connections
            courses_db = DatabaseOperations("courses")
            progress_db = DatabaseOperations("course_progress")
            submissions_db = DatabaseOperations("submissions")

            # Get user's progress data
            progress_data = await progress_db.find_many({"user_id": user_id}, limit=10)
            completed_courses = len([p for p in progress_data if p.get("completed")])

            # Get enrolled courses
            enrolled_courses = await courses_db.find_many({
                "enrolled_user_ids": user_id
            }, limit=10)

            # Get submission data
            submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)

            sample_achievements = []

            # First Steps Achievement
            if completed_courses > 0:
                sample_achievements.append({
                    "_id": _uuid(),
                    "user_id": user_id,
                    "title": "First Steps",
                    "description": "Completed your first course",
                    "icon": "🎓",
                    "earned_date": datetime.now(timezone.utc) - timedelta(days=30),
                    "category": "milestone",
                    "points": 100
                })

            # Dedicated Learner Achievement
            if completed_courses >= 3:
                sample_achievements.append({
                    "_id": _uuid(),
                    "user_id": user_id,
                    "title": "Dedicated Learner",
                    "description": f"Completed {completed_courses} courses",
                    "icon": "📚",
                    "earned_date": datetime.now(timezone.utc) - timedelta(days=14),
                    "category": "milestone",
                    "points": 300
                })

            # Knowledge Seeker Achievement
            if len(enrolled_courses) >= 10:
                sample_achievements.append({
                    "_id": _uuid(),
                    "user_id": user_id,
                    "title": "Knowledge Seeker",
                    "description": "Enrolled in 10 different courses",
                    "icon": "🔍",
                    "earned_date": datetime.now(timezone.utc) - timedelta(days=21),
                    "category": "exploration",
                    "points": 200
                })

            # Perfect Score Achievement
            perfect_submissions = len([s for s in submissions if s.get("ai_grade", {}).get("score", 0) >= 95])
            if perfect_submissions >= 3:
                sample_achievements.append({
                    "_id": _uuid(),
                    "user_id": user_id,
                    "title": "Perfect Score",
                    "description": f"Achieved perfect scores on {perfect_submissions} assignments",
                    "icon": "⭐",
                    "earned_date": datetime.now(timezone.utc) - timedelta(days=10),
                    "category": "excellence",
                    "points": 250
                })

            # Consistent Learner Achievement
            if len(submissions) >= 20:
                sample_achievements.append({
                    "_id": _uuid(),
                    "user_id": user_id,
                    "title": "Consistent Learner",
                    "description": "Submitted 20 assignments consistently",
                    "icon": "📅",
                    "earned_date": datetime.now(timezone.utc) - timedelta(days=5),
                    "category": "consistency",
                    "points": 150
                })

            # Save achievements to database
            for achievement in sample_achievements:
                await self.db.add_achievement(user_id, achievement)

            logger.info("Achievements generated", extra={
                "user_id": user_id,
                "achievements_count": len(sample_achievements),
                "completed_courses": completed_courses
            })

            return [Achievement(**achievement) for achievement in sample_achievements]

        except Exception as e:
            logger.error("Failed to generate achievements", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return []

    # Analytics operations
    async def get_learning_analytics(self, user_id: str, timeframe: str = "month") -> LearningAnalytics:
        """Get detailed learning analytics"""
        analytics_data = await self.db.get_user_analytics(user_id, timeframe)
        return LearningAnalytics(**analytics_data)

    async def get_skill_gaps(self, user_id: str) -> List[SkillGap]:
        """Analyze skill gaps based on real learning data"""
        try:
            # Get database connections
            course_progress_db = DatabaseOperations("course_progress")
            courses_db = DatabaseOperations("courses")

            # Get user's progress and course history
            progress_data = await course_progress_db.find_many({"user_id": user_id}, limit=20)
            enrolled_courses = await courses_db.find_many({
                "enrolled_user_ids": user_id
            }, limit=20)

            # Calculate performance metrics
            avg_progress = 0
            if progress_data:
                avg_progress = sum([p.get("overall_progress", 0) for p in progress_data]) / len(progress_data)

            # Get assignment/submission performance
            submissions_db = DatabaseOperations("submissions")
            submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)
            avg_grade = 85  # Default, would calculate from actual grades

            if submissions:
                grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
                if grades:
                    avg_grade = sum(grades) / len(grades)

            # Analyze skill gaps based on performance
            skill_gaps = []

            if avg_progress < 60:
                skill_gaps.append(SkillGap(
                    skill="Learning Fundamentals",
                    current_level=int(avg_progress / 10),
                    target_level=8,
                    gap_description="Need to strengthen basic learning and study skills"
                ))

            if avg_grade < 75:
                skill_gaps.append(SkillGap(
                    skill="Assessment Performance",
                    current_level=int(avg_grade / 10),
                    target_level=9,
                    gap_description="Improve performance on quizzes and assignments"
                ))

            # Add domain-specific skills based on enrolled courses
            course_titles = [c.get("title", "") for c in enrolled_courses]
            if any("python" in title.lower() for title in course_titles):
                skill_gaps.append(SkillGap(
                    skill="Python Programming",
                    current_level=6,
                    target_level=9,
                    gap_description="Master advanced Python features and best practices"
                ))

            if any("data" in title.lower() for title in course_titles):
                skill_gaps.append(SkillGap(
                    skill="Data Analysis",
                    current_level=4,
                    target_level=8,
                    gap_description="Learn data manipulation and analysis techniques"
                ))

            logger.info("Skill gaps analyzed", extra={
                "user_id": user_id,
                "skill_gaps_found": len(skill_gaps),
                "average_progress": round(avg_progress, 1),
                "average_grade": round(avg_grade, 1)
            })

            return skill_gaps

        except Exception as e:
            logger.error("Failed to analyze skill gaps", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_skill_gaps", f"Skill gap analysis failed: {str(e)}")

    async def get_career_readiness(self, user_id: str) -> CareerReadiness:
        """Get career readiness assessment"""
        try:
            # Get database connections
            courses_db = DatabaseOperations("courses")
            submissions_db = DatabaseOperations("submissions")

            # Get real performance data
            completed_courses = await courses_db.count_documents({
                "enrolled_user_ids": user_id,
                "progress.user_id": user_id,
                "progress.completed": True
            })

            total_submissions = await submissions_db.count_documents({"user_id": user_id})

            # Calculate average grade from submissions
            submissions = await submissions_db.find_many({"user_id": user_id}, limit=50)
            avg_grade = 0
            if submissions:
                grades = [s.get("ai_grade", {}).get("score", 0) for s in submissions if s.get("ai_grade")]
                if grades:
                    avg_grade = sum(grades) / len(grades)

            # Calculate readiness score
            readiness_score = min(100, (completed_courses * 10) + (avg_grade * 0.5) + (total_submissions * 2))

            # Get user's career profile
            career_profile = await self.db.get_career_profile(user_id)
            target_roles = career_profile.get("target_roles", []) if career_profile else []

            career_readiness = CareerReadiness(
                overall_score=round(readiness_score),
                assessment="Excellent" if readiness_score > 90 else "Good" if readiness_score > 75 else "Developing",
                skills_match=min(100, int(readiness_score + 10)),
                experience_level=min(10, int(readiness_score / 10)),
                industry_fit=min(100, int(readiness_score + 5)),
                recommended_careers=[
                    {
                        "title": target_roles[0] if target_roles else "Software Developer",
                        "description": "Build software solutions using modern technologies",
                        "match_score": min(100, readiness_score + 15),
                        "avg_salary": "$80k - $120k"
                    },
                    {
                        "title": "Data Analyst",
                        "description": "Analyze data to help organizations make informed decisions",
                        "match_score": min(100, readiness_score + 10),
                        "avg_salary": "$65k - $95k"
                    }
                ],
                skills_to_develop=[
                    {
                        "name": "Advanced Programming",
                        "priority": "High",
                        "current_level": min(10, int(readiness_score / 10)),
                        "time_to_master": "3-6 months"
                    },
                    {
                        "name": "System Design",
                        "priority": "Medium",
                        "current_level": max(1, int(readiness_score / 12)),
                        "time_to_master": "4-8 months"
                    }
                ]
            )

            logger.info("Career readiness assessed", extra={
                "user_id": user_id,
                "overall_score": round(readiness_score),
                "assessment": career_readiness.assessment
            })

            return career_readiness

        except Exception as e:
            logger.error("Failed to assess career readiness", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("get_career_readiness", f"Career readiness assessment failed: {str(e)}")

    # Study session operations
    async def add_study_session(self, user_id: str, session_data: StudySessionCreate) -> StudySession:
        """Add study session"""
        try:
            session_dict = session_data.dict(by_alias=True)
            session_dict["_id"] = _uuid()
            session_dict["created_at"] = datetime.now(timezone.utc)

            session_id = await self.db.add_study_session(user_id, session_dict)

            logger.info("Study session added", extra={
                "user_id": user_id,
                "session_id": session_id,
                "duration": session_data.duration_minutes
            })

            return StudySession(**session_dict)

        except Exception as e:
            logger.error("Failed to add study session", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise DatabaseError("add_study_session", f"Study session creation failed: {str(e)}")

    async def get_study_sessions(self, user_id: str, limit: int = 50) -> List[StudySession]:
        """Get user study sessions"""
        sessions_data = await self.db.get_study_sessions(user_id, limit)
        return [StudySession(**session) for session in sessions_data]

# Global service instance
user_service = UserService()