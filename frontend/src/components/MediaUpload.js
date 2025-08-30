import React, { useState, useRef, useCallback } from "react";
import api from "../services/api";

function MediaUpload({
  onMediaUploaded,
  courseId,
  lessonId,
  acceptedTypes = {
    images: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    videos: ['video/mp4', 'video/webm', 'video/ogg'],
    documents: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    audio: ['audio/mpeg', 'audio/wav', 'audio/ogg']
  },
  maxSize = 50 * 1024 * 1024 // 50MB
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadedMedia, setUploadedMedia] = useState([]);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [previewMedia, setPreviewMedia] = useState(null);
  const fileInputRef = useRef(null);

  const allAcceptedTypes = [
    ...acceptedTypes.images,
    ...acceptedTypes.videos,
    ...acceptedTypes.documents,
    ...acceptedTypes.audio
  ];

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFiles(files);
    }
  }, []);

  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      await handleFiles(files);
    }
  };

  const handleFiles = async (files) => {
    // Validate files
    const validFiles = [];
    const errors = [];

    for (const file of files) {
      if (file.size > maxSize) {
        errors.push(`${file.name}: File too large (max ${maxSize / (1024 * 1024)}MB)`);
        continue;
      }

      if (!allAcceptedTypes.includes(file.type)) {
        errors.push(`${file.name}: Unsupported file type`);
        continue;
      }

      validFiles.push(file);
    }

    if (errors.length > 0) {
      setError(errors.join('\n'));
      return;
    }

    if (validFiles.length === 0) return;

    setUploading(true);
    setError("");

    try {
      const uploadPromises = validFiles.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);

        // Add metadata for course content
        if (courseId) formData.append("course_id", courseId);
        if (lessonId) formData.append("lesson_id", lessonId);
        formData.append("media_type", getMediaType(file.type));

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
          mediaType: getMediaType(file.type),
          url: `/api/files/${response.data.file_id}`,
          uploadedAt: new Date().toISOString(),
          courseId,
          lessonId
        };
      });

      const uploadedMediaData = await Promise.all(uploadPromises);
      setUploadedMedia(prev => [...prev, ...uploadedMediaData]);

      if (onMediaUploaded) {
        onMediaUploaded(uploadedMediaData);
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setError("Failed to upload media. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const getMediaType = (fileType) => {
    if (acceptedTypes.images.includes(fileType)) return 'image';
    if (acceptedTypes.videos.includes(fileType)) return 'video';
    if (acceptedTypes.audio.includes(fileType)) return 'audio';
    if (acceptedTypes.documents.includes(fileType)) return 'document';
    return 'unknown';
  };

  const removeMedia = (mediaId) => {
    setUploadedMedia(prev => prev.filter(media => media.id !== mediaId));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getMediaIcon = (mediaType, fileType) => {
    switch (mediaType) {
      case 'image': return '🖼️';
      case 'video': return '🎥';
      case 'audio': return '🎵';
      case 'document':
        if (fileType.includes('pdf')) return '📄';
        if (fileType.includes('word')) return '📝';
        return '📄';
      default: return '📎';
    }
  };

  const previewFile = (media) => {
    if (media.mediaType === 'image') {
      setPreviewMedia(media);
    }
  };

  const closePreview = () => {
    setPreviewMedia(null);
  };

  return (
    <div className="media-upload">
      <div
        className={`upload-area ${dragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={allAcceptedTypes.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <div className="upload-content">
          <div className="upload-icon">📁</div>
          <div className="upload-text">
            <p>Drag & drop media files here or click to browse</p>
            <p className="upload-types">
              Supported: Images, Videos, Audio, Documents
            </p>
          </div>
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
              'Choose Files'
            )}
          </button>
        </div>

        <div className="upload-info">
          <p>Maximum file size: {maxSize / (1024 * 1024)}MB</p>
          <p>Supported formats: JPG, PNG, GIF, MP4, PDF, DOC, MP3, WAV</p>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error.split('\n').map((err, index) => (
            <div key={index}>{err}</div>
          ))}
        </div>
      )}

      {uploadedMedia.length > 0 && (
        <div className="uploaded-media">
          <h4>Uploaded Media ({uploadedMedia.length})</h4>
          <div className="media-grid">
            {uploadedMedia.map((media) => (
              <div key={media.id} className="media-item">
                <div className="media-preview">
                  {media.mediaType === 'image' ? (
                    <img
                      src={media.url}
                      alt={media.name}
                      onClick={() => previewFile(media)}
                      style={{ cursor: 'pointer' }}
                    />
                  ) : (
                    <div className="media-icon" onClick={() => previewFile(media)}>
                      {getMediaIcon(media.mediaType, media.type)}
                    </div>
                  )}
                </div>
                <div className="media-info">
                  <div className="media-name" title={media.name}>
                    {media.name.length > 20 ? media.name.substring(0, 20) + '...' : media.name}
                  </div>
                  <div className="media-meta">
                    <span className="media-type">{media.mediaType}</span>
                    <span className="media-size">{formatFileSize(media.size)}</span>
                  </div>
                </div>
                <div className="media-actions">
                  <button
                    className="preview-btn"
                    onClick={() => previewFile(media)}
                    title="Preview"
                  >
                    👁️
                  </button>
                  <a
                    href={media.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="download-btn"
                    title="Download"
                  >
                    📥
                  </a>
                  <button
                    className="remove-btn"
                    onClick={() => removeMedia(media.id)}
                    title="Remove"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {previewMedia && (
        <div className="media-preview-modal" onClick={closePreview}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{previewMedia.name}</h3>
              <button className="close-btn" onClick={closePreview}>×</button>
            </div>
            <div className="modal-body">
              {previewMedia.mediaType === 'image' ? (
                <img src={previewMedia.url} alt={previewMedia.name} className="preview-image" />
              ) : (
                <div className="preview-placeholder">
                  <div className="preview-icon">{getMediaIcon(previewMedia.mediaType, previewMedia.type)}</div>
                  <p>{previewMedia.name}</p>
                  <p className="file-info">
                    {previewMedia.mediaType} • {formatFileSize(previewMedia.size)}
                  </p>
                  <a href={previewMedia.url} target="_blank" rel="noopener noreferrer" className="download-link">
                    Download File
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        .media-upload {
          margin: 1rem 0;
        }

        .upload-area {
          border: 2px dashed #ddd;
          border-radius: 12px;
          padding: 2rem;
          text-align: center;
          background: #fafafa;
          transition: all 0.3s ease;
          cursor: pointer;
        }

        .upload-area:hover,
        .upload-area.drag-over {
          border-color: #667eea;
          background: #f0f2ff;
          transform: scale(1.02);
        }

        .upload-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
        }

        .upload-icon {
          font-size: 3rem;
          color: #667eea;
        }

        .upload-text p {
          margin: 0;
          color: #2c3e50;
          font-weight: 500;
        }

        .upload-types {
          color: #6c757d !important;
          font-size: 0.9rem !important;
          font-weight: normal !important;
        }

        .upload-btn {
          background: #667eea;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
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
          display: inline-block;
          margin-right: 0.5rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .upload-info {
          margin-top: 1rem;
          color: #6c757d;
          font-size: 0.85rem;
        }

        .upload-info p {
          margin: 0.25rem 0;
        }

        .error-message {
          color: #dc3545;
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          padding: 1rem;
          border-radius: 8px;
          margin-top: 1rem;
          white-space: pre-line;
        }

        .uploaded-media {
          margin-top: 2rem;
        }

        .uploaded-media h4 {
          margin: 0 0 1rem 0;
          color: #2c3e50;
          font-size: 1.1rem;
        }

        .media-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }

        .media-item {
          background: white;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: transform 0.3s;
        }

        .media-item:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .media-preview {
          height: 150px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f8f9fa;
          overflow: hidden;
        }

        .media-preview img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .media-icon {
          font-size: 3rem;
          color: #667eea;
          cursor: pointer;
        }

        .media-info {
          padding: 1rem;
        }

        .media-name {
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
        }

        .media-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.8rem;
          color: #6c757d;
        }

        .media-type {
          text-transform: capitalize;
          background: #e9ecef;
          padding: 0.25rem 0.5rem;
          border-radius: 12px;
        }

        .media-actions {
          padding: 0.5rem;
          display: flex;
          justify-content: space-between;
          background: #f8f9fa;
        }

        .media-actions button,
        .media-actions a {
          background: none;
          border: none;
          cursor: pointer;
          padding: 0.5rem;
          border-radius: 4px;
          transition: background 0.3s;
          font-size: 0.9rem;
        }

        .media-actions button:hover,
        .media-actions a:hover {
          background: rgba(0,0,0,0.1);
        }

        .preview-btn {
          color: #007bff;
        }

        .download-btn {
          color: #28a745;
          text-decoration: none;
        }

        .remove-btn {
          color: #dc3545;
        }

        .media-preview-modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal-content {
          background: white;
          border-radius: 12px;
          width: 90%;
          max-width: 800px;
          max-height: 90vh;
          overflow: hidden;
          box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .modal-header {
          padding: 1.5rem;
          border-bottom: 1px solid #e9ecef;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .modal-header h3 {
          margin: 0;
          color: #2c3e50;
          font-size: 1.2rem;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 2rem;
          cursor: pointer;
          color: #6c757d;
          padding: 0;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: background 0.3s;
        }

        .close-btn:hover {
          background: #f8f9fa;
        }

        .modal-body {
          padding: 1.5rem;
          text-align: center;
        }

        .preview-image {
          max-width: 100%;
          max-height: 60vh;
          border-radius: 8px;
          box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .preview-placeholder {
          padding: 3rem;
        }

        .preview-placeholder .preview-icon {
          font-size: 4rem;
          color: #667eea;
          margin-bottom: 1rem;
        }

        .preview-placeholder p {
          margin: 0.5rem 0;
          color: #2c3e50;
          font-weight: 500;
        }

        .file-info {
          color: #6c757d !important;
          font-size: 0.9rem !important;
        }

        .download-link {
          display: inline-block;
          margin-top: 1rem;
          padding: 0.75rem 1.5rem;
          background: #667eea;
          color: white;
          text-decoration: none;
          border-radius: 6px;
          transition: background 0.3s;
        }

        .download-link:hover {
          background: #5a67d8;
        }

        @media (max-width: 768px) {
          .media-grid {
            grid-template-columns: 1fr;
          }

          .upload-area {
            padding: 1.5rem;
          }

          .media-actions {
            flex-direction: column;
            gap: 0.25rem;
          }
        }
      `}</style>
    </div>
  );
}

export default MediaUpload;