import React, { useState, useRef } from "react";
import api from "../services/api";

function FileUpload({ onFileUploaded, multiple = false, accept = "*/*", maxSize = 10 * 1024 * 1024 }) {
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files);
    if (!files.length) return;

    // Validate file sizes
    const oversizedFiles = files.filter(file => file.size > maxSize);
    if (oversizedFiles.length > 0) {
      setError(`Some files exceed the maximum size of ${maxSize / (1024 * 1024)}MB`);
      return;
    }

    setUploading(true);
    setError("");

    try {
      const uploadPromises = files.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await api.post("/files/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });

        return {
          id: response.data.file_id,
          name: response.data.filename,
          size: file.size,
          type: file.type,
          uploadedAt: new Date().toISOString()
        };
      });

      const uploadedFileData = await Promise.all(uploadPromises);
      setUploadedFiles(prev => [...prev, ...uploadedFileData]);

      if (onFileUploaded) {
        onFileUploaded(multiple ? uploadedFileData : uploadedFileData[0]);
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setError("Failed to upload files. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const removeFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileType) => {
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType.startsWith('video/')) return '🎥';
    if (fileType.startsWith('audio/')) return '🎵';
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('word') || fileType.includes('document')) return '📝';
    if (fileType.includes('spreadsheet') || fileType.includes('excel')) return '📊';
    if (fileType.includes('presentation') || fileType.includes('powerpoint')) return '📽️';
    if (fileType.includes('zip') || fileType.includes('rar')) return '📦';
    return '📄';
  };

  return (
    <div className="file-upload">
      <div className="upload-area">
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={accept}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <button
          type="button"
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <span className="spinner"></span>
              Uploading...
            </>
          ) : (
            <>
              📎 Choose Files
            </>
          )}
        </button>

        <p className="upload-info">
          Maximum file size: {maxSize / (1024 * 1024)}MB
          {accept !== "*/*" && ` • Accepted types: ${accept}`}
        </p>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {uploadedFiles.length > 0 && (
        <div className="uploaded-files">
          <h4>Uploaded Files:</h4>
          <div className="file-list">
            {uploadedFiles.map((file) => (
              <div key={file.id} className="file-item">
                <div className="file-info">
                  <span className="file-icon">{getFileIcon(file.type)}</span>
                  <div className="file-details">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="remove-btn"
                  onClick={() => removeFile(file.id)}
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        .file-upload {
          margin: 1rem 0;
        }

        .upload-area {
          border: 2px dashed #ddd;
          border-radius: 8px;
          padding: 2rem;
          text-align: center;
          background: #fafafa;
          transition: all 0.3s;
        }

        .upload-area:hover {
          border-color: #667eea;
          background: #f0f2ff;
        }

        .upload-btn {
          background: #667eea;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          transition: all 0.3s;
        }

        .upload-btn:hover:not(:disabled) {
          background: #5a67d8;
          transform: translateY(-1px);
        }

        .upload-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
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

        .upload-info {
          margin: 1rem 0 0 0;
          color: #6c757d;
          font-size: 0.9rem;
        }

        .error-message {
          color: #dc3545;
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          padding: 0.75rem;
          border-radius: 6px;
          margin-top: 1rem;
        }

        .uploaded-files {
          margin-top: 1.5rem;
        }

        .uploaded-files h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
          font-size: 1rem;
        }

        .file-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem;
          background: white;
          border: 1px solid #e9ecef;
          border-radius: 6px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .file-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .file-icon {
          font-size: 1.5rem;
        }

        .file-details {
          display: flex;
          flex-direction: column;
        }

        .file-name {
          font-weight: 500;
          color: #2c3e50;
          margin-bottom: 0.25rem;
        }

        .file-size {
          font-size: 0.8rem;
          color: #6c757d;
        }

        .remove-btn {
          background: #dc3545;
          color: white;
          border: none;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.8rem;
          transition: all 0.3s;
        }

        .remove-btn:hover {
          background: #c82333;
          transform: scale(1.1);
        }
      `}</style>
    </div>
  );
}

export default FileUpload;