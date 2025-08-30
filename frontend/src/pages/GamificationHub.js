import React, { useEffect, useState } from "react";
import api from "../services/api";

function GamificationHub() {
  const [userStats, setUserStats] = useState(null);
  const [badges, setBadges] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadUserStats();
    loadBadges();
    loadLeaderboard();
    loadAchievements();
  }, []);

  const loadUserStats = async () => {
    try {
      // This would be a real API call in production
      setUserStats({
        totalPoints: 1250,
        currentStreak: 7,
        longestStreak: 14,
        coursesCompleted: 3,
        assignmentsSubmitted: 12,
        quizScore: 88,
        rank: 15,
        level: 3
      });
    } catch (error) {
      console.error("Error loading user stats:", error);
    }
  };

  const loadBadges = async () => {
    try {
      // Mock data - would come from API
      setBadges([
        {
          id: "1",
          name: "First Steps",
          description: "Complete your first lesson",
          icon: "🎯",
          earned: true,
          earnedDate: "2024-01-15"
        },
        {
          id: "2",
          name: "Quiz Master",
          description: "Score 90% or higher on 5 quizzes",
          icon: "🧠",
          earned: true,
          earnedDate: "2024-01-20"
        },
        {
          id: "3",
          name: "Streak Champion",
          description: "Maintain a 7-day learning streak",
          icon: "🔥",
          earned: true,
          earnedDate: "2024-01-25"
        },
        {
          id: "4",
          name: "Course Conqueror",
          description: "Complete 3 courses",
          icon: "🏆",
          earned: false,
          progress: 3,
          target: 3
        }
      ]);
    } catch (error) {
      console.error("Error loading badges:", error);
    }
  };

  const loadLeaderboard = async () => {
    try {
      // Mock data - would come from API
      setLeaderboard([
        { rank: 1, name: "Alice Johnson", points: 2450, avatar: "👩‍🎓" },
        { rank: 2, name: "Bob Smith", points: 2230, avatar: "👨‍💻" },
        { rank: 3, name: "Carol Davis", points: 2100, avatar: "👩‍🔬" },
        { rank: 4, name: "David Wilson", points: 1980, avatar: "👨‍🏫" },
        { rank: 5, name: "Emma Brown", points: 1850, avatar: "👩‍🎨" },
        { rank: 15, name: "You", points: 1250, avatar: "🎓", isCurrentUser: true }
      ]);
    } catch (error) {
      console.error("Error loading leaderboard:", error);
    }
  };

  const loadAchievements = async () => {
    try {
      // Mock data - would come from API
      setAchievements([
        {
          id: "1",
          title: "Week Warrior",
          description: "Study for 7 consecutive days",
          points: 100,
          icon: "⚔️",
          unlocked: true,
          unlockedDate: "2024-01-25"
        },
        {
          id: "2",
          title: "Knowledge Seeker",
          description: "Complete 10 lessons",
          points: 150,
          icon: "📚",
          unlocked: true,
          unlockedDate: "2024-01-20"
        },
        {
          id: "3",
          title: "Perfect Score",
          description: "Get 100% on a quiz",
          points: 200,
          icon: "💯",
          unlocked: false,
          progress: 95,
          target: 100
        }
      ]);
    } catch (error) {
      console.error("Error loading achievements:", error);
    }
  };

  return (
    <div className="gamification-hub">
      <div className="hub-header">
        <h1>🎮 Gamification Hub</h1>
        <p>Track your progress, earn badges, and climb the leaderboard!</p>
      </div>

      <div className="hub-tabs">
        <button
          className={activeTab === "overview" ? "active" : ""}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          className={activeTab === "badges" ? "active" : ""}
          onClick={() => setActiveTab("badges")}
        >
          Badges
        </button>
        <button
          className={activeTab === "leaderboard" ? "active" : ""}
          onClick={() => setActiveTab("leaderboard")}
        >
          Leaderboard
        </button>
        <button
          className={activeTab === "achievements" ? "active" : ""}
          onClick={() => setActiveTab("achievements")}
        >
          Achievements
        </button>
      </div>

      <div className="hub-content">
        {activeTab === "overview" && userStats && (
          <div className="overview-section">
            <div className="stats-grid">
              <div className="stat-card primary">
                <div className="stat-icon">⭐</div>
                <div className="stat-content">
                  <div className="stat-value">{userStats.totalPoints.toLocaleString()}</div>
                  <div className="stat-label">Total Points</div>
                </div>
              </div>

              <div className="stat-card streak">
                <div className="stat-icon">🔥</div>
                <div className="stat-content">
                  <div className="stat-value">{userStats.currentStreak}</div>
                  <div className="stat-label">Day Streak</div>
                </div>
              </div>

              <div className="stat-card level">
                <div className="stat-icon">📊</div>
                <div className="stat-content">
                  <div className="stat-value">Level {userStats.level}</div>
                  <div className="stat-label">Current Level</div>
                </div>
              </div>

              <div className="stat-card rank">
                <div className="stat-icon">🏅</div>
                <div className="stat-content">
                  <div className="stat-value">#{userStats.rank}</div>
                  <div className="stat-label">Global Rank</div>
                </div>
              </div>
            </div>

            <div className="progress-section">
              <h3>Recent Achievements</h3>
              <div className="recent-achievements">
                {achievements.slice(0, 3).map(achievement => (
                  <div key={achievement.id} className="achievement-item">
                    <div className="achievement-icon">{achievement.icon}</div>
                    <div className="achievement-content">
                      <h4>{achievement.title}</h4>
                      <p>{achievement.description}</p>
                      <div className="achievement-points">+{achievement.points} points</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "badges" && (
          <div className="badges-section">
            <h2>Your Badges</h2>
            <div className="badges-grid">
              {badges.map(badge => (
                <div key={badge.id} className={`badge-card ${badge.earned ? 'earned' : 'locked'}`}>
                  <div className="badge-icon">{badge.icon}</div>
                  <div className="badge-content">
                    <h3>{badge.name}</h3>
                    <p>{badge.description}</p>
                    {badge.earned ? (
                      <div className="badge-status earned">
                        <span>✓ Earned</span>
                        <small>{new Date(badge.earnedDate).toLocaleDateString()}</small>
                      </div>
                    ) : (
                      <div className="badge-status locked">
                        <span>🔒 Locked</span>
                        {badge.progress && (
                          <small>{badge.progress}/{badge.target}</small>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "leaderboard" && (
          <div className="leaderboard-section">
            <h2>Global Leaderboard</h2>
            <div className="leaderboard-list">
              {leaderboard.map((user, index) => (
                <div
                  key={user.rank}
                  className={`leaderboard-item ${user.isCurrentUser ? 'current-user' : ''}`}
                >
                  <div className="rank">
                    {user.rank <= 3 ? (
                      <span className={`rank-badge rank-${user.rank}`}>
                        {user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : '🥉'}
                      </span>
                    ) : (
                      <span className="rank-number">#{user.rank}</span>
                    )}
                  </div>
                  <div className="user-avatar">{user.avatar}</div>
                  <div className="user-info">
                    <div className="user-name">{user.name}</div>
                    <div className="user-points">{user.points.toLocaleString()} points</div>
                  </div>
                  {user.isCurrentUser && <div className="current-user-badge">You</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "achievements" && (
          <div className="achievements-section">
            <h2>Achievements</h2>
            <div className="achievements-list">
              {achievements.map(achievement => (
                <div key={achievement.id} className={`achievement-card ${achievement.unlocked ? 'unlocked' : 'locked'}`}>
                  <div className="achievement-icon">{achievement.icon}</div>
                  <div className="achievement-content">
                    <h3>{achievement.title}</h3>
                    <p>{achievement.description}</p>
                    <div className="achievement-meta">
                      <span className="points">+{achievement.points} points</span>
                      {achievement.unlocked ? (
                        <span className="status unlocked">✓ Unlocked</span>
                      ) : (
                        <span className="status locked">
                          🔒 {achievement.progress || 0}/{achievement.target || 100}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .gamification-hub {
          min-height: 100vh;
          background: #f8f9fa;
          padding: 2rem;
        }

        .hub-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .hub-header h1 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .hub-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .hub-tabs {
          display: flex;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .hub-tabs button {
          flex: 1;
          padding: 0.75rem 1rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-radius: 8px;
          font-weight: 500;
          transition: all 0.3s;
        }

        .hub-tabs button.active {
          background: #667eea;
          color: white;
        }

        .hub-content {
          max-width: 1200px;
          margin: 0 auto;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
          margin-bottom: 3rem;
        }

        .stat-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .stat-card.primary {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
        }

        .stat-card.streak {
          background: linear-gradient(135deg, #f093fb, #f5576c);
          color: white;
        }

        .stat-card.level {
          background: linear-gradient(135deg, #4facfe, #00f2fe);
          color: white;
        }

        .stat-card.rank {
          background: linear-gradient(135deg, #43e97b, #38f9d7);
          color: white;
        }

        .stat-icon {
          font-size: 2rem;
        }

        .stat-content {
          flex: 1;
        }

        .stat-value {
          font-size: 1.5rem;
          font-weight: bold;
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.9rem;
          opacity: 0.9;
        }

        .badges-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .badge-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          display: flex;
          align-items: center;
          gap: 1rem;
          transition: transform 0.3s;
        }

        .badge-card:hover {
          transform: translateY(-5px);
        }

        .badge-card.locked {
          opacity: 0.6;
        }

        .badge-icon {
          font-size: 3rem;
        }

        .badge-content h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .badge-content p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .badge-status {
          font-size: 0.8rem;
          font-weight: 500;
        }

        .badge-status.earned {
          color: #28a745;
        }

        .badge-status.locked {
          color: #6c757d;
        }

        .leaderboard-list {
          background: white;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .leaderboard-item {
          display: flex;
          align-items: center;
          padding: 1rem 1.5rem;
          border-bottom: 1px solid #e9ecef;
          transition: background 0.3s;
        }

        .leaderboard-item:hover {
          background: #f8f9fa;
        }

        .leaderboard-item.current-user {
          background: #e3f2fd;
          border-left: 4px solid #2196f3;
        }

        .leaderboard-item:last-child {
          border-bottom: none;
        }

        .rank {
          width: 60px;
          text-align: center;
        }

        .rank-badge {
          font-size: 1.5rem;
        }

        .rank-number {
          font-weight: bold;
          color: #6c757d;
        }

        .user-avatar {
          font-size: 2rem;
          margin-right: 1rem;
        }

        .user-info {
          flex: 1;
        }

        .user-name {
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 0.25rem;
        }

        .user-points {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .current-user-badge {
          background: #2196f3;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .achievements-list {
          display: grid;
          gap: 1rem;
        }

        .achievement-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .achievement-card.locked {
          opacity: 0.6;
        }

        .achievement-icon {
          font-size: 2.5rem;
        }

        .achievement-content h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .achievement-content p {
          margin: 0.5rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .achievement-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
        }

        .points {
          background: #28a745;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .status.unlocked {
          color: #28a745;
          font-weight: 500;
        }

        .status.locked {
          color: #6c757d;
          font-weight: 500;
        }

        .progress-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .progress-section h3 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .recent-achievements {
          display: grid;
          gap: 1rem;
        }

        .achievement-item {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
        }

        .achievement-points {
          color: #28a745;
          font-weight: 500;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
          .hub-tabs {
            flex-direction: column;
          }

          .stats-grid {
            grid-template-columns: 1fr;
          }

          .stat-card {
            padding: 1.5rem;
          }

          .badges-grid {
            grid-template-columns: 1fr;
          }

          .leaderboard-item {
            padding: 1rem;
          }
        }
      `}</style>
    </div>
  );
}

export default GamificationHub;