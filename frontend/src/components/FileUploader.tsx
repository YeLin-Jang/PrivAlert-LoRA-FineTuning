import React, { useRef } from 'react';
import { validateFile, validateFileCount, validateVideoFile } from '../utils/validation';
import { formatFileSize } from '../utils/formatters';
import { UPLOAD_LIMITS } from '../constants';

interface FileUploaderProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  isVideo?: boolean;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
  files,
  onFilesChange,
  accept,
  multiple = true,
  maxFiles = UPLOAD_LIMITS.MAX_FILES,
  isVideo = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;

    const newFiles = Array.from(e.target.files);
    const allFiles = [...files, ...newFiles];

    // 파일 개수 검증
    const countCheck = validateFileCount(allFiles);
    if (!countCheck.isValid) {
      alert(countCheck.error);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    // 각 파일 검증
    const validFiles: File[] = [];
    for (const file of newFiles) {
      // 비디오 파일인 경우 비동기 검증 (길이 검증 포함)
      if (isVideo) {
        const validation = await validateVideoFile(file);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          alert(`${file.name}: ${validation.error}`);
        }
      } else {
        // 이미지 파일인 경우 동기 검증
        const validation = validateFile(file, isVideo);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          alert(`${file.name}: ${validation.error}`);
        }
      }
    }

    if (validFiles.length > 0) {
      onFilesChange([...files, ...validFiles]);
    }

    // 파일 입력 필드 초기화
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    onFilesChange(newFiles);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="file-uploader">
      <input
        ref={fileInputRef}
        type="file"
        accept={accept || (isVideo ? 'video/*' : 'image/*')}
        multiple={multiple}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        aria-label="파일 업로드"
      />
      
      <button type="button" onClick={handleClick} className="upload-button">
        📁 {isVideo ? '비디오' : '이미지'} 파일 선택
      </button>

      {files.length > 0 && (
        <div className="file-list">
          <h4>선택된 파일 ({files.length}/{maxFiles})</h4>
          <ul>
            {files.map((file, index) => (
              <li key={index} className="file-item">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="remove-button"
                  aria-label={`${file.name} 제거`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

