import React, { useEffect, useState } from "react";
import api from "../services/api";

function Marketplace() {
    const [activeTab, setActiveTab] = useState("courses");
    const [courses, setCourses] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [internships, setInternships] = useState([]);
    const [careerMatches, setCareerMatches] = useState(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [filters, setFilters] = useState({
        category: "",
        minPrice: "",
        maxPrice: "",
        location: "",
        jobType: "",
        skills: ""
    });

    useEffect(() => {
        loadMarketplaceData();
    }, [activeTab]);

    const loadMarketplaceData = async () => {
        try {
            if (activeTab === "courses") {
                const res = await api.get("/marketplace/courses/marketplace", {
                    params: {
                        search: searchTerm,
                        category: filters.category,
                        min_price: filters.minPrice,
                        max_price: filters.maxPrice
                    }
                });
                setCourses(res.data);
            } else if (activeTab === "jobs") {
                const res = await api.get("/marketplace/jobs", {
                    params: {
                        search: searchTerm,
                        location: filters.location,
                        job_type: filters.jobType,
                        skills: filters.skills
                    }
                });
                setJobs(res.data);
            } else if (activeTab === "internships") {
                const res = await api.get("/marketplace/internships", {
                    params: {
                        search: searchTerm,
                        skills: filters.skills
                    }
                });
                setInternships(res.data);
            } else if (activeTab === "career") {
                const res = await api.get("/marketplace/career/matches");
                setCareerMatches(res.data);
            }
        } catch (error) {
            console.error("Failed to load marketplace data:", error);
        }
    };

    const purchaseCourse = async (course) => {
        if (!confirm(`Purchase "${course.title}" for $${course.price}?`)) return;

        try {
            const res = await api.post(`/marketplace/courses/marketplace/${course._id}/purchase`, {
                buyer_tenant_id: "default", // In production, get from user context
                payment_method: "card" // Simplified
            });
            alert("Purchase successful! Course access granted.");
            loadMarketplaceData();
        } catch (error) {
            alert("Purchase failed. Please try again.");
        }
    };

    const applyForJob = async (job) => {
        if (!confirm(`Apply for "${job.title}" at ${job.company}?`)) return;

        try {
            // In production, this would upload resume and send application
            alert("Application submitted successfully!");
        } catch (error) {
            alert("Application failed. Please try again.");
        }
    };

    const applyForInternship = async (internship) => {
        if (!confirm(`Apply for "${internship.title}" internship at ${internship.company}?`)) return;

        try {
            // In production, this would upload resume and send application
            alert("Internship application submitted successfully!");
        } catch (error) {
            alert("Application failed. Please try again.");
        }
    };

    const updateCareerProfile = async () => {
        const profileData = {
            career_goals: ["Software Developer", "Tech Lead"],
            target_industries: ["Technology", "Finance"],
            target_roles: ["Full Stack Developer", "DevOps Engineer"],
            skills_to_develop: ["React", "Node.js", "AWS"],
            resume_data: {},
            linkedin_profile: "https://linkedin.com/in/example"
        };

        try {
            await api.post("/marketplace/career/profile", profileData);
            alert("Career profile updated!");
            loadMarketplaceData();
        } catch (error) {
            alert("Failed to update profile");
        }
    };

    return (
        <div className="marketplace">
            <div className="marketplace-header">
                <h1>🛒 Learning Marketplace</h1>
                <p>Discover courses, jobs, internships, and career opportunities</p>
            </div>

            <div className="marketplace-tabs">
                <button
                    className={activeTab === "courses" ? "active" : ""}
                    onClick={() => setActiveTab("courses")}
                >
                    📚 Courses
                </button>
                <button
                    className={activeTab === "jobs" ? "active" : ""}
                    onClick={() => setActiveTab("jobs")}
                >
                    💼 Jobs
                </button>
                <button
                    className={activeTab === "internships" ? "active" : ""}
                    onClick={() => setActiveTab("internships")}
                >
                    🎓 Internships
                </button>
                <button
                    className={activeTab === "career" ? "active" : ""}
                    onClick={() => setActiveTab("career")}
                >
                    🎯 Career Services
                </button>
            </div>

            <div className="marketplace-content">
                {/* Search and Filters */}
                <div className="search-filters">
                    <div className="search-bar">
                        <input
                            type="text"
                            placeholder={`Search ${activeTab}...`}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onKeyPress={(e) => e.key === "Enter" && loadMarketplaceData()}
                        />
                        <button onClick={loadMarketplaceData}>🔍</button>
                    </div>

                    {activeTab === "courses" && (
                        <div className="filters">
                            <select
                                value={filters.category}
                                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                            >
                                <option value="">All Categories</option>
                                <option value="programming">Programming</option>
                                <option value="design">Design</option>
                                <option value="business">Business</option>
                                <option value="science">Science</option>
                            </select>
                            <input
                                type="number"
                                placeholder="Min Price"
                                value={filters.minPrice}
                                onChange={(e) => setFilters({ ...filters, minPrice: e.target.value })}
                            />
                            <input
                                type="number"
                                placeholder="Max Price"
                                value={filters.maxPrice}
                                onChange={(e) => setFilters({ ...filters, maxPrice: e.target.value })}
                            />
                        </div>
                    )}

                    {activeTab === "jobs" && (
                        <div className="filters">
                            <input
                                type="text"
                                placeholder="Location"
                                value={filters.location}
                                onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                            />
                            <select
                                value={filters.jobType}
                                onChange={(e) => setFilters({ ...filters, jobType: e.target.value })}
                            >
                                <option value="">All Types</option>
                                <option value="full_time">Full Time</option>
                                <option value="part_time">Part Time</option>
                                <option value="contract">Contract</option>
                                <option value="internship">Internship</option>
                            </select>
                            <input
                                type="text"
                                placeholder="Skills (comma separated)"
                                value={filters.skills}
                                onChange={(e) => setFilters({ ...filters, skills: e.target.value })}
                            />
                        </div>
                    )}

                    {activeTab === "internships" && (
                        <div className="filters">
                            <input
                                type="text"
                                placeholder="Required Skills"
                                value={filters.skills}
                                onChange={(e) => setFilters({ ...filters, skills: e.target.value })}
                            />
                            <label>
                                <input
                                    type="checkbox"
                                    onChange={(e) => setFilters({ ...filters, remoteOnly: e.target.checked })}
                                />
                                Remote Only
                            </label>
                        </div>
                    )}
                </div>

                {/* Courses Tab */}
                {activeTab === "courses" && (
                    <div className="courses-grid">
                        {courses.map(course => (
                            <div key={course._id} className="course-card">
                                <div className="course-image">
                                    📚
                                </div>
                                <div className="course-info">
                                    <h3>{course.title}</h3>
                                    <p className="course-description">
                                        {course.description || "Comprehensive course content"}
                                    </p>
                                    <div className="course-meta">
                                        <span className="price">${course.price}</span>
                                        <span className="rating">⭐ {course.rating?.toFixed(1) || "N/A"}</span>
                                        <span className="students">👥 {course.enrolled_count || 0} students</span>
                                    </div>
                                    <div className="course-tags">
                                        {course.tags?.map(tag => (
                                            <span key={tag} className="tag">{tag}</span>
                                        ))}
                                    </div>
                                    <button
                                        className="btn primary"
                                        onClick={() => purchaseCourse(course)}
                                    >
                                        Purchase Course
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Jobs Tab */}
                {activeTab === "jobs" && (
                    <div className="jobs-list">
                        {jobs.map(job => (
                            <div key={job._id} className="job-card">
                                <div className="job-header">
                                    <h3>{job.title}</h3>
                                    <span className="company">{job.company}</span>
                                </div>
                                <p className="job-description">{job.description}</p>
                                <div className="job-details">
                                    <span className="location">📍 {job.location}</span>
                                    <span className="salary">
                                        💰 {job.salary_range || "Competitive"}
                                    </span>
                                    <span className="type">🏢 {job.job_type?.replace("_", " ")}</span>
                                </div>
                                <div className="job-skills">
                                    {job.skills_required?.map(skill => (
                                        <span key={skill} className="skill-tag">{skill}</span>
                                    ))}
                                </div>
                                <button
                                    className="btn primary"
                                    onClick={() => applyForJob(job)}
                                >
                                    Apply Now
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Internships Tab */}
                {activeTab === "internships" && (
                    <div className="internships-list">
                        {internships.map(internship => (
                            <div key={internship._id} className="internship-card">
                                <div className="internship-header">
                                    <h3>{internship.title}</h3>
                                    <span className="company">{internship.company}</span>
                                </div>
                                <p className="internship-description">{internship.description}</p>
                                <div className="internship-details">
                                    <span className="duration">⏱️ {internship.duration_weeks} weeks</span>
                                    <span className="compensation">
                                        💰 {internship.compensation || "Paid"}
                                    </span>
                                    {internship.remote_allowed && (
                                        <span className="remote">🏠 Remote OK</span>
                                    )}
                                </div>
                                <div className="internship-skills">
                                    <h4>Skills you'll develop:</h4>
                                    {internship.skills_developed?.map(skill => (
                                        <span key={skill} className="skill-tag">{skill}</span>
                                    ))}
                                </div>
                                <button
                                    className="btn primary"
                                    onClick={() => applyForInternship(internship)}
                                >
                                    Apply for Internship
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Career Services Tab */}
                {activeTab === "career" && (
                    <div className="career-services">
                        <div className="career-profile-section">
                            <h2>🎯 Your Career Profile</h2>
                            <p>Update your career goals and preferences to get personalized recommendations</p>
                            <button className="btn primary" onClick={updateCareerProfile}>
                                Update Career Profile
                            </button>
                        </div>

                        {careerMatches && (
                            <div className="career-matches">
                                <h2>🚀 Personalized Recommendations</h2>

                                {careerMatches.job_matches?.length > 0 && (
                                    <div className="matches-section">
                                        <h3>💼 Recommended Jobs</h3>
                                        <div className="matches-grid">
                                            {careerMatches.job_matches.slice(0, 3).map(job => (
                                                <div key={job._id} className="match-card">
                                                    <h4>{job.title}</h4>
                                                    <p>{job.company}</p>
                                                    <span className="match-reason">Matches your career goals</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {careerMatches.internship_matches?.length > 0 && (
                                    <div className="matches-section">
                                        <h3>🎓 Recommended Internships</h3>
                                        <div className="matches-grid">
                                            {careerMatches.internship_matches.slice(0, 3).map(internship => (
                                                <div key={internship._id} className="match-card">
                                                    <h4>{internship.title}</h4>
                                                    <p>{internship.company}</p>
                                                    <span className="match-reason">Develops your target skills</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {careerMatches.course_matches?.length > 0 && (
                                    <div className="matches-section">
                                        <h3>📚 Recommended Courses</h3>
                                        <div className="matches-grid">
                                            {careerMatches.course_matches.slice(0, 3).map(course => (
                                                <div key={course._id} className="match-card">
                                                    <h4>{course.title}</h4>
                                                    <p>{course.audience} • {course.difficulty}</p>
                                                    <span className="match-reason">Builds required skills</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="career-tools">
                            <h2>🛠️ Career Development Tools</h2>
                            <div className="tools-grid">
                                <div className="tool-card">
                                    <h3>📄 Resume Builder</h3>
                                    <p>Create professional resumes with AI assistance</p>
                                    <button className="btn secondary">Build Resume</button>
                                </div>
                                <div className="tool-card">
                                    <h3>🎤 Interview Prep</h3>
                                    <p>Practice interviews with AI feedback</p>
                                    <button className="btn secondary">Start Practice</button>
                                </div>
                                <div className="tool-card">
                                    <h3>📊 Skills Assessment</h3>
                                    <p>Assess your current skill levels</p>
                                    <button className="btn secondary">Take Assessment</button>
                                </div>
                                <div className="tool-card">
                                    <h3>🤝 Networking Hub</h3>
                                    <p>Connect with professionals and alumni</p>
                                    <button className="btn secondary">Explore Network</button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <style jsx>{`
        .marketplace {
          min-height: 100vh;
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          padding: 2rem;
        }

        .marketplace-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .marketplace-header h1 {
          background: linear-gradient(135deg, #667eea, #764ba2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          font-size: 2.5rem;
          margin-bottom: 0.5rem;
        }

        .marketplace-header p {
          color: #6c757d;
          font-size: 1.1rem;
        }

        .marketplace-tabs {
          display: flex;
          justify-content: center;
          margin-bottom: 2rem;
          background: white;
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .marketplace-tabs button {
          padding: 0.75rem 1.5rem;
          border: none;
          background: transparent;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          color: #6c757d;
        }

        .marketplace-tabs button.active {
          background: #667eea;
          color: white;
        }

        .marketplace-tabs button:hover {
          background: #f8f9fa;
        }

        .marketplace-content {
          max-width: 1200px;
          margin: 0 auto;
        }

        .search-filters {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          margin-bottom: 2rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .search-bar {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .search-bar input {
          flex: 1;
          padding: 0.75rem 1rem;
          border: 2px solid #e9ecef;
          border-radius: 8px;
          font-size: 1rem;
        }

        .search-bar button {
          padding: 0.75rem 1.5rem;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 1rem;
        }

        .filters {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .filters select, .filters input {
          padding: 0.5rem 1rem;
          border: 2px solid #e9ecef;
          border-radius: 8px;
          font-size: 0.9rem;
        }

        .courses-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .course-card {
          background: white;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          transition: transform 0.3s;
        }

        .course-card:hover {
          transform: translateY(-5px);
        }

        .course-image {
          height: 150px;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 3rem;
          color: white;
        }

        .course-info {
          padding: 1.5rem;
        }

        .course-info h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .course-description {
          color: #6c757d;
          margin-bottom: 1rem;
          line-height: 1.5;
        }

        .course-meta {
          display: flex;
          justify-content: space-between;
          margin-bottom: 1rem;
          font-size: 0.9rem;
        }

        .price {
          font-weight: bold;
          color: #28a745;
          font-size: 1.1rem;
        }

        .rating {
          color: #ffc107;
        }

        .students {
          color: #6c757d;
        }

        .course-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .tag {
          padding: 0.25rem 0.5rem;
          background: #e9ecef;
          color: #495057;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .jobs-list, .internships-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .job-card, .internship-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .job-header, .internship-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .job-header h3, .internship-header h3 {
          margin: 0;
          color: #2c3e50;
        }

        .company {
          color: #667eea;
          font-weight: 600;
        }

        .job-description, .internship-description {
          color: #6c757d;
          margin-bottom: 1rem;
          line-height: 1.5;
        }

        .job-details, .internship-details {
          display: flex;
          gap: 2rem;
          margin-bottom: 1rem;
          font-size: 0.9rem;
        }

        .location, .salary, .type, .duration, .compensation, .remote {
          color: #495057;
        }

        .job-skills, .internship-skills {
          margin-bottom: 1rem;
        }

        .job-skills h4, .internship-skills h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 0.9rem;
        }

        .skill-tag {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          background: #667eea;
          color: white;
          border-radius: 12px;
          font-size: 0.8rem;
          margin-right: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .career-services {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .career-profile-section {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          text-align: center;
        }

        .career-matches {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .matches-section {
          margin-bottom: 2rem;
        }

        .matches-section h3 {
          color: #2c3e50;
          margin-bottom: 1rem;
        }

        .matches-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem;
        }

        .match-card {
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 8px;
          border-left: 4px solid #667eea;
        }

        .match-card h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .match-card p {
          margin: 0.25rem 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .match-reason {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          background: #28a745;
          color: white;
          border-radius: 12px;
          font-size: 0.8rem;
        }

        .career-tools {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .tools-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }

        .tool-card {
          padding: 1.5rem;
          background: #f8f9fa;
          border-radius: 8px;
          text-align: center;
        }

        .tool-card h3 {
          color: #2c3e50;
          margin-bottom: 0.5rem;
        }

        .tool-card p {
          color: #6c757d;
          margin-bottom: 1rem;
          font-size: 0.9rem;
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn.primary {
          background: #667eea;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 768px) {
          .marketplace-tabs {
            flex-direction: column;
          }

          .courses-grid {
            grid-template-columns: 1fr;
          }

          .matches-grid {
            grid-template-columns: 1fr;
          }

          .tools-grid {
            grid-template-columns: 1fr;
          }

          .filters {
            flex-direction: column;
          }

          .job-details, .internship-details {
            flex-direction: column;
            gap: 0.5rem;
          }
        }
      `}</style>
        </div>
    );
}

export default Marketplace;