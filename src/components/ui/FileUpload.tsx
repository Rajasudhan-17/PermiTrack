import React, { useState, useRef } from 'react';
import { UploadCloud, File, X, CheckCircle2 } from 'lucide-react';

export interface FileUploadProps {
  label?: string;
  helperText?: string;
  accept?: string;
  maxSizeMB?: number;
  error?: string;
  disabled?: boolean;
  onFileSelect?: (file: File | null) => void;
  className?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  label,
  helperText = 'PNG, JPG, PDF up to 10MB',
  accept = '.png,.jpg,.jpeg,.pdf',
  maxSizeMB = 10,
  error,
  disabled = false,
  onFileSelect,
  className = '',
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (file.size > maxSizeMB * 1024 * 1024) {
      setLocalError(`File size exceeds ${maxSizeMB}MB limit`);
      return;
    }
    setLocalError(null);
    setSelectedFile(file);
    if (onFileSelect) onFileSelect(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = '';
    if (onFileSelect) onFileSelect(null);
  };

  const activeError = error || localError;

  return (
    <div className={`w-full flex flex-col gap-1.5 ${className}`}>
      {label && (
        <span className="text-xs font-medium text-text-secondary select-none">{label}</span>
      )}
      
      {!selectedFile ? (
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => !disabled && inputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2 ${
            dragActive
              ? 'border-primary bg-primary-subtle'
              : activeError
              ? 'border-danger/50 bg-danger-subtle'
              : 'border-border hover:border-border-hover bg-bg-secondary/50'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            disabled={disabled}
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
          <div className="w-10 h-10 rounded-full bg-surface-elevated flex items-center justify-center text-primary">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div className="text-sm text-text-primary font-medium">
            Click to upload <span className="text-text-muted font-normal">or drag and drop</span>
          </div>
          <div className="text-xs text-text-muted">{helperText}</div>
        </div>
      ) : (
        <div className="flex items-center justify-between p-3 bg-surface-elevated rounded-lg border border-border">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 rounded bg-primary-subtle text-primary flex items-center justify-center shrink-0">
              <File className="w-4 h-4" />
            </div>
            <div className="truncate">
              <div className="text-sm font-medium text-text-primary truncate">{selectedFile.name}</div>
              <div className="text-xs text-text-muted">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</div>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRemove}
            className="text-text-muted hover:text-danger p-1 rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {activeError && (
        <span className="text-xs text-danger font-medium">{activeError}</span>
      )}
    </div>
  );
};
