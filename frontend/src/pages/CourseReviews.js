import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

function CourseReviews({ me }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [discussions, setDiscussions] = useState([]);
  const [selectedDiscussion, setSelectedDiscussion] = useState(null);
  const [discussionReplies, setDiscussionReplies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("reviews");
  const [showNewDiscussion, setShowNewDiscussion] = useState(false);
  const [newDiscussion, setNewDiscussion] = useState({
    title: "",
    content: "",
    discussion_type: "question",
    tags: []
  });
  const [newReply, setNewReply] = useState("");
  const [replying, setReplying] = useState(false);

  useEffect(() => {
    loadData();
  }, [courseId]);

  const loadData = async () => {
    try {
      const [courseRes, reviewsRes, discussionsRes] = await Promise.all([
        api.get(`/courses/${courseId}`),
        api.get(`/reviews/courses/${courseId}/reviews`),
        api.get(`/discussions/courses/${courseId}/threads`)
      ]);

      setCourse(courseRes.data);
      setReviews(reviewsRes.data);
      // Transform discussions data to match expected format
      setDiscussions(discussionsRes.data.map(discussion => ({
        ...discussion,
        id: discussion._id,
        title: discussion.title,
        content: discussion.body,
        user_name: discussion.user_id,
        created_at: discussion.created_at,
        is_locked: discussion.locked,
        is_pinned: discussion.pinned,
        is_featured: discussion.featured,
        discussion_type: 'question', // Default type
        reply_count: discussion.reply_count || 0,
        view_count: discussion.view_count || 0,
        upvote_count: discussion.upvote_count || 0
      })));
    } catch (error) {
      console.error("Error loading data:", error);
      alert("Error loading course data");
    } finally {
      setLoading(false);
    }
  };

  const submitReview = async (reviewData) => {
    try {
      await api.post(`/reviews/courses/${courseId}/reviews`, reviewData);
      alert("Review submitted successfully!");
      loadData();
    } catch (error) {
      console.error("Error submitting review:", error);
      alert("Error submitting review");
    }
  };

  const createDiscussion = async () => {
    try {
      await api.post(`/discussions/courses/${courseId}/threads`, {
        title: newDiscussion.title,
        body: newDiscussion.content
      });
      setShowNewDiscussion(false);
      setNewDiscussion({
        title: "",
        content: "",
        discussion_type: "question",
        tags: []
      });
      loadData();
      alert("Discussion created successfully!");
    } catch (error) {
      console.error("Error creating discussion:", error);
      alert("Error creating discussion");
    }
  };

  const loadDiscussionDetails = async (discussionId) => {
    try {
      const [threadRes, postsRes] = await Promise.all([
        api.get(`/discussions/threads/${discussionId}`),
        api.get(`/discussions/threads/${discussionId}/posts`)
      ]);

      // Transform the data to match the expected format
      setSelectedDiscussion({
        ...threadRes.data,
        id: threadRes.data._id,
        title: threadRes.data.title,
        content: threadRes.data.body,
        user_name: threadRes.data.user_id,
        created_at: threadRes.data.created_at,
        is_locked: threadRes.data.locked,
        is_pinned: threadRes.data.pinned,
        is_featured: threadRes.data.featured
      });

      setDiscussionReplies(postsRes.data.map(post => ({
        id: post._id,
        content: post.body,
        user_name: post.user_id,
        created_at: post.created_at,
        is_solution: post.is_solution,
        is_instructor_reply: false // We'll need to check this from user role
      })));
    } catch (error) {
      console.error("Error loading discussion:", error);
      alert("Error loading discussion details");
    }
  };

  const submitReply = async (discussionId) => {
    if (!newReply.trim()) return;

    setReplying(true);
    try {
      await api.post(`/discussions/threads/${discussionId}/posts`, {
        body: newReply
      });
      setNewReply("");
      loadDiscussionDetails(discussionId);
      alert("Reply posted successfully!");
    } catch (error) {
      console.error("Error posting reply:", error);
      alert("Error posting reply");
    } finally {
      setReplying(false);
    }
  };

  const voteOnReview = async (reviewId, voteType) => {
    try {
      await api.post(`/reviews/reviews/${reviewId}/vote`, { vote_type: voteType });
      loadData();
    } catch (error) {
      console.error("Error voting on review:", error);
    }
  };

  const pinDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/pin`);
      loadData();
    } catch (error) {
      console.error("Error pinning discussion:", error);
      alert("Error updating discussion");
    }
  };

  const unpinDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/unpin`);
      loadData();
    } catch (error) {
      console.error("Error unpinning discussion:", error);
      alert("Error updating discussion");
    }
  };

  const lockDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/lock`);
      loadData();
    } catch (error) {
      console.error("Error locking discussion:", error);
      alert("Error updating discussion");
    }
  };

  const unlockDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/unlock`);
      loadData();
    } catch (error) {
      console.error("Error unlocking discussion:", error);
      alert("Error updating discussion");
    }
  };

  const featureDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/featured`);
      loadData();
    } catch (error) {
      console.error("Error featuring discussion:", error);
      alert("Error updating discussion");
    }
  };

  const unfeatureDiscussion = async (discussionId) => {
    try {
      await api.put(`/discussions/threads/${discussionId}/unfeature`);
      loadData();
    } catch (error) {
      console.error("Error unfeaturing discussion:", error);
      alert("Error updating discussion");
    }
  };

  const markReplyAsSolution = async (replyId) => {
    try {
      await api.put(`/discussions/posts/${replyId}/solution`);
      if (selectedDiscussion) {
        loadDiscussionDetails(selectedDiscussion.id);
      }
    } catch (error) {
      console.error("Error marking reply as solution:", error);
      alert("Error updating reply");
    }
  };

  const deleteDiscussion = async (discussionId) => {
    if (!confirm("Are you sure you want to delete this discussion?")) return;

    try {
      await api.delete(`/discussions/threads/${discussionId}`);
      loadData();
      if (selectedDiscussion && selectedDiscussion.id === discussionId) {
        setSelectedDiscussion(null);
      }
      alert("Discussion deleted successfully!");
    } catch (error) {
      console.error("Error deleting discussion:", error);
      alert("Error deleting discussion");
    }
  };

  const deleteReply = async (replyId) => {
    if (!confirm("Are you sure you want to delete this reply?")) return;

    try {
      await api.delete(`/discussions/posts/${replyId}`);
      if (selectedDiscussion) {
        loadDiscussionDetails(selectedDiscussion.id);
      }
      alert("Reply deleted successfully!");
    } catch (error) {
      console.error("Error deleting reply:", error);
      alert("Error deleting reply");
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading course reviews...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="error-container">
        <h2>Course not found</h2>
        <button onClick={() => navigate("/instructor")}>Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="course-reviews">
      <div className="reviews-header">
        <div className="header-content">
          <button className="back-btn" onClick={() => navigate("/instructor")}>
            ← Back to Dashboard
          </button>
          <div className="course-info">
            <h1>{course.title} - Reviews & Q&A</h1>
            <div className="course-meta">
              <span>{course.audience}</span>
              <span>•</span>
              <span>{course.difficulty}</span>
              <span>•</span>
              <span>{reviews.length} reviews</span>
              <span>•</span>
              <span>{discussions.length} discussions</span>
            </div>
          </div>
        </div>
      </div>

      <div className="reviews-tabs">
        <button
          className={activeTab === "reviews" ? "active" : ""}
          onClick={() => setActiveTab("reviews")}
        >
          Reviews ({reviews.length})
        </button>
        <button
          className={activeTab === "discussions" ? "active" : ""}
          onClick={() => setActiveTab("discussions")}
        >
          Q&A ({discussions.length})
        </button>
      </div>

      <div className="reviews-content">
        {activeTab === "reviews" && (
          <div className="reviews-section">
            <div className="section-header">
              <h2>Course Reviews</h2>
              <div className="review-summary">
                <div className="rating-overview">
                  <div className="average-rating">
                    <span className="rating-number">
                      {reviews.length > 0
                        ? (reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length).toFixed(1)
                        : "0.0"
                      }
                    </span>
                    <div className="stars">
                      {'⭐'.repeat(Math.round(reviews.reduce((sum, r) => sum + r.rating, 0) / Math.max(reviews.length, 1)))}
                    </div>
                    <span className="total-reviews">({reviews.length} reviews)</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="reviews-list">
              {reviews.map(review => (
                <div key={review.id} className="review-card">
                  <div className="review-header">
                    <div className="reviewer-info">
                      <div className="reviewer-avatar">
                        {review.user_name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="reviewer-details">
                        <h4>{review.user_name || 'Anonymous'}</h4>
                        <div className="review-meta">
                          <div className="rating">
                            {'⭐'.repeat(review.rating)}
                          </div>
                          <span>•</span>
                          <span>{new Date(review.created_at).toLocaleDateString()}</span>
                          {review.is_verified_purchase && (
                            <>
                              <span>•</span>
                              <span className="verified-badge">✅ Verified Purchase</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="review-content">
                    <h5>{review.title}</h5>
                    <p>{review.content}</p>

                    {review.pros?.length > 0 && (
                      <div className="review-pros">
                        <strong>👍 What students liked:</strong>
                        <ul>
                          {review.pros.map((pro, index) => (
                            <li key={index}>{pro}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {review.cons?.length > 0 && (
                      <div className="review-cons">
                        <strong>👎 Areas for improvement:</strong>
                        <ul>
                          {review.cons.map((con, index) => (
                            <li key={index}>{con}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {review.instructor_response && (
                      <div className="instructor-response">
                        <div className="response-header">
                          <strong>👨‍🏫 Instructor Response:</strong>
                          <span className="response-date">
                            {new Date(review.response_date).toLocaleDateString()}
                          </span>
                        </div>
                        <p>{review.instructor_response}</p>
                      </div>
                    )}
                  </div>

                  <div className="review-actions">
                    <button
                      className="btn small secondary"
                      onClick={() => voteOnReview(review.id, 'helpful')}
                    >
                      👍 Helpful ({review.helpful_votes || 0})
                    </button>
                    {me?.role === 'instructor' && !review.instructor_response && (
                      <button className="btn small primary">
                        💬 Respond
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {reviews.length === 0 && (
                <div className="empty-state">
                  <h3>No reviews yet</h3>
                  <p>Reviews will appear here once students complete your course</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "discussions" && (
          <div className="discussions-section">
            <div className="section-header">
              <h2>Q&A Discussions</h2>
              <button
                className="btn primary"
                onClick={() => setShowNewDiscussion(true)}
              >
                + New Discussion
              </button>
            </div>

            {!selectedDiscussion ? (
              <div className="discussions-list">
                {discussions.map(discussion => (
                  <div key={discussion.id} className="discussion-card">
                    <div className="discussion-header">
                      <div className="discussion-info">
                        <h4>{discussion.title}</h4>
                        <div className="discussion-meta">
                          <span>by {discussion.user_name || 'Anonymous'}</span>
                          <span>•</span>
                          <span>{discussion.discussion_type}</span>
                          <span>•</span>
                          <span>{discussion.reply_count || 0} replies</span>
                          <span>•</span>
                          <span>{new Date(discussion.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="discussion-badges">
                        {discussion.is_pinned && <span className="badge pinned">📌 Pinned</span>}
                        {discussion.is_locked && <span className="badge locked">🔒 Locked</span>}
                        {discussion.is_featured && <span className="badge featured">⭐ Featured</span>}
                      </div>
                    </div>

                    <div className="discussion-preview">
                      {discussion.content?.substring(0, 200)}...
                    </div>

                    <div className="discussion-stats">
                      <span>👁️ {discussion.view_count || 0} views</span>
                      <span>❤️ {discussion.upvote_count || 0} upvotes</span>
                      <span>💬 {discussion.reply_count || 0} replies</span>
                    </div>

                    <div className="discussion-actions">
                      <button
                        className="btn small"
                        onClick={() => loadDiscussionDetails(discussion.id)}
                      >
                        View Discussion
                      </button>
                      {me?.role === 'instructor' && (
                        <>
                          {discussion.is_pinned ? (
                            <button
                              className="btn small secondary"
                              onClick={() => unpinDiscussion(discussion.id)}
                            >
                              📌 Unpin
                            </button>
                          ) : (
                            <button
                              className="btn small secondary"
                              onClick={() => pinDiscussion(discussion.id)}
                            >
                              📌 Pin
                            </button>
                          )}
                          {discussion.is_locked ? (
                            <button
                              className="btn small secondary"
                              onClick={() => unlockDiscussion(discussion.id)}
                            >
                              🔓 Unlock
                            </button>
                          ) : (
                            <button
                              className="btn small secondary"
                              onClick={() => lockDiscussion(discussion.id)}
                            >
                              🔒 Lock
                            </button>
                          )}
                          {discussion.is_featured ? (
                            <button
                              className="btn small secondary"
                              onClick={() => unfeatureDiscussion(discussion.id)}
                            >
                              ⭐ Unfeature
                            </button>
                          ) : (
                            <button
                              className="btn small secondary"
                              onClick={() => featureDiscussion(discussion.id)}
                            >
                              ⭐ Feature
                            </button>
                          )}
                          <button
                            className="btn small danger"
                            onClick={() => deleteDiscussion(discussion.id)}
                          >
                            🗑️ Delete
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}

                {discussions.length === 0 && (
                  <div className="empty-state">
                    <h3>No discussions yet</h3>
                    <p>Start the conversation by creating the first discussion</p>
                    <button
                      className="btn primary"
                      onClick={() => setShowNewDiscussion(true)}
                    >
                      Create First Discussion
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="discussion-detail">
                <div className="discussion-detail-header">
                  <button
                    className="back-btn"
                    onClick={() => setSelectedDiscussion(null)}
                  >
                    ← Back to Discussions
                  </button>
                  <div className="discussion-title">
                    <h3>{selectedDiscussion.title}</h3>
                    <div className="discussion-meta">
                      <span>by {selectedDiscussion.user_name || 'Anonymous'}</span>
                      <span>•</span>
                      <span>{selectedDiscussion.discussion_type}</span>
                      <span>•</span>
                      <span>{new Date(selectedDiscussion.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="discussion-content">
                  <p>{selectedDiscussion.content}</p>
                </div>

                <div className="replies-section">
                  <h4>{discussionReplies.length} Replies</h4>

                  <div className="replies-list">
                    {discussionReplies.map(reply => (
                      <div key={reply.id} className={`reply-card ${reply.is_solution ? 'solution' : ''}`}>
                        <div className="reply-header">
                          <div className="reply-author">
                            <div className="author-avatar">
                              {reply.user_name?.charAt(0).toUpperCase() || 'U'}
                            </div>
                            <div className="author-info">
                              <h5>{reply.user_name || 'Anonymous'}</h5>
                              <div className="reply-meta">
                                {reply.is_instructor_reply && (
                                  <span className="instructor-badge">👨‍🏫 Instructor</span>
                                )}
                                {reply.is_solution && (
                                  <span className="solution-badge">✅ Solution</span>
                                )}
                                <span>•</span>
                                <span>{new Date(reply.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>
                          <div className="reply-actions">
                            {me?.role === 'instructor' && !reply.is_solution && (
                              <button
                                className="btn small secondary"
                                onClick={() => markReplyAsSolution(reply.id)}
                              >
                                ✅ Mark as Solution
                              </button>
                            )}
                            {(me?.role === 'instructor' || me?.id === reply.user_id) && (
                              <button
                                className="btn small danger"
                                onClick={() => deleteReply(reply.id)}
                              >
                                🗑️ Delete
                              </button>
                            )}
                          </div>
                        </div>

                        <div className="reply-content">
                          <p>{reply.content}</p>
                        </div>

                        <div className="reply-stats">
                          <span>❤️ {reply.upvote_count || 0} upvotes</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {!selectedDiscussion.is_locked && (
                    <div className="reply-form">
                      <h4>Post a Reply</h4>
                      <textarea
                        value={newReply}
                        onChange={(e) => setNewReply(e.target.value)}
                        placeholder="Share your thoughts or answer this question..."
                        rows={4}
                      />
                      <button
                        className="btn primary"
                        onClick={() => submitReply(selectedDiscussion.id)}
                        disabled={replying || !newReply.trim()}
                      >
                        {replying ? "Posting..." : "Post Reply"}
                      </button>
                    </div>
                  )}

                  {selectedDiscussion.is_locked && (
                    <div className="locked-notice">
                      <p>🔒 This discussion has been locked by the instructor</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showNewDiscussion && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Create New Discussion</h3>

            <div className="discussion-form">
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={newDiscussion.title}
                  onChange={(e) => setNewDiscussion(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="What is your question or topic?"
                />
              </div>

              <div className="form-group">
                <label>Type</label>
                <select
                  value={newDiscussion.discussion_type}
                  onChange={(e) => setNewDiscussion(prev => ({ ...prev, discussion_type: e.target.value }))}
                >
                  <option value="question">Question</option>
                  <option value="discussion">Discussion</option>
                  <option value="announcement">Announcement</option>
                  <option value="clarification">Clarification</option>
                </select>
              </div>

              <div className="form-group">
                <label>Content</label>
                <textarea
                  value={newDiscussion.content}
                  onChange={(e) => setNewDiscussion(prev => ({ ...prev, content: e.target.value }))}
                  rows={6}
                  placeholder="Provide details about your question or discussion topic..."
                />
              </div>

              <div className="form-group">
                <label>Tags (optional)</label>
                <input
                  type="text"
                  placeholder="Add tags separated by commas"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ',') {
                      e.preventDefault();
                      const tag = e.target.value.trim();
                      if (tag && !newDiscussion.tags.includes(tag)) {
                        setNewDiscussion(prev => ({
                          ...prev,
                          tags: [...prev.tags, tag]
                        }));
                        e.target.value = '';
                      }
                    }
                  }}
                />
                <div className="tags-list">
                  {newDiscussion.tags.map((tag, index) => (
                    <span key={index} className="tag">
                      {tag}
                      <button
                        onClick={() => {
                          setNewDiscussion(prev => ({
                            ...prev,
                            tags: prev.tags.filter((_, i) => i !== index)
                          }));
                        }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button
                className="btn secondary"
                onClick={() => {
                  setShowNewDiscussion(false);
                  setNewDiscussion({
                    title: "",
                    content: "",
                    discussion_type: "question",
                    tags: []
                  });
                }}
              >
                Cancel
              </button>
              <button
                className="btn primary"
                onClick={createDiscussion}
                disabled={!newDiscussion.title.trim() || !newDiscussion.content.trim()}
              >
                Create Discussion
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .course-reviews {
          min-height: 100vh;
          background: #f8f9fa;
        }

        .reviews-header {
          background: white;
          padding: 2rem;
          border-bottom: 1px solid #e9ecef;
        }

        .header-content {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .back-btn {
          background: none;
          border: none;
          color: #007bff;
          cursor: pointer;
          font-weight: 500;
          align-self: flex-start;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .course-info h1 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .course-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
        }

        .reviews-tabs {
          background: white;
          display: flex;
          border-bottom: 1px solid #e9ecef;
        }

        .reviews-tabs button {
          padding: 1rem 2rem;
          border: none;
          background: none;
          color: #6c757d;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .reviews-tabs button.active {
          color: #007bff;
          border-bottom-color: #007bff;
        }

        .reviews-content {
          padding: 2rem;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .section-header h2 {
          margin: 0;
          color: #2c3e50;
        }

        .review-summary {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .average-rating {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
        }

        .rating-number {
          font-size: 3rem;
          font-weight: bold;
          color: #2c3e50;
        }

        .stars {
          font-size: 1.5rem;
        }

        .total-reviews {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .reviews-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .review-card {
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .review-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1.5rem;
        }

        .reviewer-info {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .reviewer-avatar {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: #007bff;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 1.2rem;
        }

        .reviewer-details h4 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .review-meta {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .rating {
          color: #ffc107;
          font-size: 1.1rem;
        }

        .verified-badge {
          background: #d4edda;
          color: #155724;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .review-content h5 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .review-content p {
          margin: 0 0 1rem 0;
          color: #495057;
          line-height: 1.6;
        }

        .review-pros, .review-cons {
          margin: 1rem 0;
          padding: 1rem;
          border-radius: 8px;
        }

        .review-pros {
          background: #d4edda;
          border-left: 4px solid #28a745;
        }

        .review-pros ul, .review-cons ul {
          margin: 0.5rem 0 0 0;
          padding-left: 1.5rem;
        }

        .review-pros li, .review-cons li {
          margin-bottom: 0.25rem;
          color: #495057;
        }

        .review-cons {
          background: #f8d7da;
          border-left: 4px solid #dc3545;
        }

        .instructor-response {
          margin: 1rem 0;
          padding: 1rem;
          background: #e3f2fd;
          border-left: 4px solid #2196f3;
          border-radius: 8px;
        }

        .response-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }

        .response-date {
          color: #6c757d;
          font-size: 0.9rem;
        }

        .review-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;
        }

        .discussions-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .discussion-card {
          background: white;
          padding: 1.5rem;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .discussion-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .discussion-info h4 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .discussion-meta {
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .discussion-badges {
          display: flex;
          gap: 0.5rem;
        }

        .badge {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .badge.pinned {
          background: #fff3cd;
          color: #856404;
        }

        .badge.locked {
          background: #f8d7da;
          color: #721c24;
        }

        .badge.featured {
          background: #d1ecf1;
          color: #0c5460;
        }

        .discussion-preview {
          color: #495057;
          margin-bottom: 1rem;
          line-height: 1.5;
        }

        .discussion-stats {
          display: flex;
          gap: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
          margin-bottom: 1rem;
        }

        .discussion-actions {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .discussion-detail {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .discussion-detail-header {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #e9ecef;
        }

        .discussion-title h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
        }

        .discussion-content {
          margin-bottom: 2rem;
        }

        .discussion-content p {
          color: #495057;
          line-height: 1.6;
          font-size: 1.1rem;
        }

        .replies-section h4 {
          margin: 0 0 1.5rem 0;
          color: #2c3e50;
        }

        .replies-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .reply-card {
          padding: 1.5rem;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          background: #fafafa;
        }

        .reply-card.solution {
          border-color: #28a745;
          background: #d4edda;
        }

        .reply-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .reply-author {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .author-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: #007bff;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
        }

        .author-info h5 {
          margin: 0 0 0.25rem 0;
          color: #2c3e50;
        }

        .reply-meta {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .instructor-badge, .solution-badge {
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .instructor-badge {
          background: #007bff;
          color: white;
        }

        .solution-badge {
          background: #28a745;
          color: white;
        }

        .reply-content p {
          margin: 0;
          color: #495057;
          line-height: 1.5;
        }

        .reply-stats {
          margin-top: 1rem;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .reply-form {
          background: #f8f9fa;
          padding: 1.5rem;
          border-radius: 8px;
        }

        .reply-form h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
        }

        .reply-form textarea {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          margin-bottom: 1rem;
          font-family: inherit;
          resize: vertical;
        }

        .locked-notice {
          text-align: center;
          padding: 2rem;
          background: #fff3cd;
          border-radius: 8px;
          color: #856404;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: white;
          border-radius: 12px;
          width: 90%;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
        }

        .modal h3 {
          margin: 0 0 2rem 0;
          padding: 2rem 2rem 0;
          color: #2c3e50;
        }

        .discussion-form {
          padding: 0 2rem;
        }

        .form-group {
          margin-bottom: 1.5rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: #2c3e50;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .tags-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 0.5rem;
        }

        .tag {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.25rem 0.75rem;
          background: #e9ecef;
          border-radius: 20px;
          font-size: 0.9rem;
        }

        .tag button {
          background: none;
          border: none;
          color: #6c757d;
          cursor: pointer;
          font-size: 1.2rem;
          line-height: 1;
        }

        .modal-actions {
          padding: 2rem;
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
          border-top: 1px solid #e9ecef;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .empty-state h3 {
          margin: 0 0 1rem 0;
          color: #6c757d;
        }

        .empty-state p {
          margin: 0 0 2rem 0;
          color: #6c757d;
        }

        .btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s;
        }

        .btn.primary {
          background: #007bff;
          color: white;
        }

        .btn.secondary {
          background: #6c757d;
          color: white;
        }

        .btn.small {
          padding: 0.375rem 0.75rem;
          font-size: 0.875rem;
        }

        .btn.danger {
          background: #dc3545;
          color: white;
        }

        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 400px;
          gap: 1rem;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-container {
          text-align: center;
          padding: 3rem;
        }

        .error-container h2 {
          color: #dc3545;
          margin-bottom: 2rem;
        }
      `}</style>
    </div>
  );
}

export default CourseReviews;