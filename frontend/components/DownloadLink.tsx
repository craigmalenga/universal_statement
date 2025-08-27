// frontend/components/DownloadLink.tsx
import { useState } from 'react'

interface DownloadLinkProps {
  url: string
  filename: string
  type: 'excel' | 'csv'
}

export default function DownloadLink({ url, filename, type }: DownloadLinkProps) {
  const [isDownloading, setIsDownloading] = useState(false)

  const handleDownload = async () => {
    setIsDownloading(true)
    
    try {
      const downloadUrl = `/api${url}`
      const response = await fetch(downloadUrl)
      
      if (!response.ok) {
        throw new Error('Download failed')
      }
      
      const blob = await response.blob()
      const downloadUrl2 = window.URL.createObjectURL(blob)
      
      // Create temporary download link
      const link = document.createElement('a')
      link.href = downloadUrl2
      link.download = filename
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl2)
      
    } catch (error) {
      console.error('Download failed:', error)
      alert('Download failed. Please try again.')
    } finally {
      setIsDownloading(false)
    }
  }

  const getFileIcon = () => {
    if (type === 'excel') {
      return (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M16.004 3.999H8.003c-1.100 0-2 .9-2 2v12c0 1.100.9 2 2 2h8c1.100 0 2-.9 2-2v-12c0-1.100-.899-2-1.999-2zm-1 14H9.003v-1h6v1zm0-2H9.003v-1h6v1zm0-2H9.003v-1h6v1zm0-2H9.003v-1h6v1zm0-2H9.003v-1h6v1zm0-2H9.003v-1h6v1z" />
        </svg>
      )
    }
    
    return (
      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.89 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
      </svg>
    )
  }

  const getButtonStyle = () => {
    if (type === 'excel') {
      return 'bg-green-600 hover:bg-green-700 text-white'
    }
    return 'bg-blue-600 hover:bg-blue-700 text-white'
  }

  const getTypeLabel = () => {
    if (type === 'excel') return 'Excel'
    return 'CSV'
  }

  const getTypeDescription = () => {
    if (type === 'excel') {
      return 'Formatted spreadsheet with styling'
    }
    return 'Plain text format for data analysis'
  }

  return (
    <div className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
            type === 'excel' ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'
          }`}>
            {getFileIcon()}
          </div>
          
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">
              Download {getTypeLabel()}
            </h3>
            <p className="text-sm text-gray-500">
              {getTypeDescription()}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {filename}
            </p>
          </div>
        </div>
        
        <button
          onClick={handleDownload}
          disabled={isDownloading}
          className={`
            px-6 py-3 rounded-lg font-medium transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-offset-2
            disabled:opacity-50 disabled:cursor-not-allowed
            ${getButtonStyle()}
            ${type === 'excel' ? 'focus:ring-green-500' : 'focus:ring-blue-500'}
          `}
        >
          {isDownloading ? (
            <div className="flex items-center space-x-2">
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Downloading...</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Download</span>
            </div>
          )}
        </button>
      </div>
      
      {/* File format details */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Format: .{type === 'excel' ? 'xlsx' : 'csv'}</span>
          <span>Structured data ready for analysis</span>
        </div>
      </div>
    </div>
  )
}