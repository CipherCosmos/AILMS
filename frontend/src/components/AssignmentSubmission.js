import React, { useState } from "react";
import api from "../services/api";
import FileUpload from "./FileUpload";

function AssignmentSubmission({ assignment, courseId, onSubmitted }) {
  const [textAnswer, setTextAnswer] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleFileUploaded = (files) => {
    if (Array.isArray(files)) {
      setUploadedFiles(files);
    } else {
      setUploadedFiles([files]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!textAnswer.trim() && uploadedFiles.length === 0) {
      setError("Please provide either a text answer or upload files");
      return;
    }

    setSubmitting(true);

    try {
      const submissionData = {
        text_answer: textAnswer.trim() || null,
        file_ids: uploadedFiles.map(file => file.id)
      };

      await api.post(`/assignments/${assignment.id}/submit`, submissionData);

      if (onSubmitted) {
        onSubmitted();
      }

      // Reset form
      setTextAnswer("");
      setUploadedFiles([]);
      alert("Assignment submitted successfully!");

    } catch (error) {
      console.error("Submission failed:", error);
      setError(error.response?.data?.detail || "Failed to submit assignment");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="assignment-submission">
      <div className="assignment-header">
        <h3>{assignment.title}</h3>
        <p>{assignment.description}</p>
        {assignment.due_at && (
          <div className="due-date">
            <strong>Due:</strong> {new Date(assignment.due_at).toLocaleDateString()}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="submission-form">
        <div className="form-group">
          <label htmlFor="text-answer">Your Answer:</label>
          <textarea
            id="text-answer"
            value={textAnswer}
            onChange={(e) => setTextAnswer(e.target.value)}
            placeholder="Write your answer here..."
            rows={6}
            className="text-input"
          />
        </div>

        <div className="form-group">
          <label>Attachments:</label>
          <FileUpload
            onFileUploaded={handleFileUploaded}
            multiple={true}
            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.zip"
            maxSize={20 * 1024 * 1024} // 20MB
          />
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="form-actions">
          <button
            type="submit"
            className="submit-btn"
            disabled={submitting}
          >
            {submitting ? (
              <>
                <span className="spinner"></span>
                Submitting...
              </>
            ) : (
              "Submit Assignment"
            )}
          </button>
        </div>
      </form>

      <style jsx>{`
        .assignment-submission {
          background: white;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          margin: 1rem 0;
        }

        .assignment-header {
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #e9ecef;
        }

        .assignment-header h3 {
          margin: 0 0 0.5rem 0;
          color: #2c3e50;
          font-size: 1.25rem;
        }

        .assignment-header p {
          margin: 0.5rem 0;
          color: #6c757d;
          line-height: 1.5;
        }

        .due-date {
          color: #dc3545;
          font-size: 0.9rem;
          margin-top: 0.5rem;
        }

        .submission-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .form-group label {
          font-weight: 600;
          color: #2c3e50;
        }

        .text-input {
          width: 100%;
          padding: 1rem;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-family: inherit;
          font-size: 1rem;
          line-height: 1.5;
          resize: vertical;
          transition: border-color 0.3s;
        }

        .text-input:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .error-message {
          color: #dc3545;
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          padding: 0.75rem;
          border-radius: 6px;
          font-size: 0.9rem;
        }

        .form-actions {
          display: flex;
          justify-content: flex-end;
          padding-top: 1rem;
          border-top: 1px solid #e9ecef;
        }

        .submit-btn {
          background: #28a745;
          color: white;
          border: none;
          padding: 0.75rem 2rem;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          transition: all 0.3s;
        }

        .submit-btn:hover:not(:disabled) {
          background: #218838;
          transform: translateY(-1px);
        }

        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #ffffff;
          border-top: 2px solid transparent;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .assignment-submission {
            padding: 1rem;
          }

          .form-actions {
            flex-direction: column;
          }

          .submit-btn {
            width: 100%;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
}

export default AssignmentSubmission;