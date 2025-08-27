// frontend/pages/index.tsx - ENHANCED WITH DEBUGGING
import { useState, useEffect } from 'react'
import Head from 'next/head'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/ProgressBar'
import DownloadLink from '../components/DownloadLink'
import DebugPanel from '../components/DebugPanel'

// At the top of the component, inside Home()
console.log('API URL:', process.env.NEXT_PUBLIC_API_URL || 'NOT SET')

interface ConversionResult {
  session_id: string
  transactions_count: number
  excel_url: string
  csv_url: string
  processing_time?: number
  success: boolean
  debug_logs?: DebugLog[]
  raw_content_preview?: string
  extraction_details?: any
  parsing_details?: any
  sample_transactions?: any[]
}

interface DebugLog {
  timestamp: string
  level: string
  message: string
  data?: any
}

interface ErrorResponse {
  error: boolean
  message: string
  session_id?: string
  debug_logs?: DebugLog[]
  raw_content?: string
  traceback?: string
}

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [result, setResult] = useState<ConversionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorDetails, setErrorDetails] = useState<ErrorResponse | null>(null)
  const [debugMode, setDebugMode] = useState(true)
  const [showDebugPanel, setShowDebugPanel] = useState(false)
  const [debugLogs, setDebugLogs] = useState<DebugLog[]>([])
  const [apiHealth, setApiHealth] = useState<any>(null)

  // Check API health on mount
  useEffect(() => {
    checkApiHealth()
  }, [])

  const checkApiHealth = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch('/api/health')
      const data = await response.json()
      setApiHealth(data)
      console.log('API Health:', data)
    } catch (error) {
      console.error('API Health Check Failed:', error)

      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setApiHealth({ status: 'error', message: errorMessage })

    }
  }

  const handleFileUpload = async (file: File) => {
    console.log('Starting file upload:', file.name, 'Size:', file.size)
    
    setIsProcessing(true)
    setProgress(0)
    setProgressMessage('Initializing...')
    setResult(null)
    setError(null)
    setErrorDetails(null)
    setDebugLogs([])

    try {
      const formData = new FormData()
      formData.append('file', file)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      // Add debug parameter
      const uploadUrl = `/api/convert?debug=${debugMode}`
      
      console.log('Uploading to:', uploadUrl)
      setProgress(10)
      setProgressMessage('Uploading file...')

      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
      })

      console.log('Response status:', response.status)
      const data = await response.json()
      console.log('Response data:', data)

      if (!response.ok || data.error) {
        // Handle error response
        const errorData = data as ErrorResponse
        
        setError(errorData.message || 'Conversion failed')
        setErrorDetails(errorData)
        
        // Store debug logs if available
        if (errorData.debug_logs) {
          setDebugLogs(errorData.debug_logs)
        }
        
        // Show debug panel on error
        if (debugMode) {
          setShowDebugPanel(true)
        }
        
        console.error('Conversion failed:', errorData)
        return
      }

      // Success
      const resultData = data as ConversionResult
      
      setProgress(100)
      setProgressMessage('Conversion complete!')
      setResult(resultData)
      
      // Store debug logs
      if (resultData.debug_logs) {
        setDebugLogs(resultData.debug_logs)
      }
      
      console.log('Conversion successful:', resultData)

      // Auto-cleanup after 30 minutes
      setTimeout(() => {
        fetch(`/api/cleanup/${resultData.session_id}`, { method: 'DELETE' })
      }, 30 * 60 * 1000)

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An error occurred'
      setError(`Network error: ${errorMsg}`)
      setProgress(0)
      console.error('Network error:', err)
    } finally {
      setIsProcessing(false)
    }
  }

  const resetForm = () => {
    setResult(null)
    setError(null)
    setErrorDetails(null)
    setProgress(0)
    setProgressMessage('')
    setDebugLogs([])
    setShowDebugPanel(false)
  }

  // Update progress based on debug logs
  useEffect(() => {
    if (debugLogs.length > 0 && isProcessing) {
      const lastLog = debugLogs[debugLogs.length - 1]
      
      // Update progress based on log messages
      if (lastLog.message.includes('Saving uploaded file')) {
        setProgress(20)
        setProgressMessage('Saving file...')
      } else if (lastLog.message.includes('Starting PDF content extraction')) {
        setProgress(30)
        setProgressMessage('Extracting content from PDF...')
      } else if (lastLog.message.includes('Attempting text extraction')) {
        setProgress(40)
        setProgressMessage('Reading PDF text...')
      } else if (lastLog.message.includes('trying OCR')) {
        setProgress(50)
        setProgressMessage('Using OCR to read scanned document...')
      } else if (lastLog.message.includes('Starting transaction parsing')) {
        setProgress(60)
        setProgressMessage('Parsing transactions...')
      } else if (lastLog.message.includes('Trying standard UK format')) {
        setProgress(65)
        setProgressMessage('Analyzing UK bank format...')
      } else if (lastLog.message.includes('Trying tabular format')) {
        setProgress(70)
        setProgressMessage('Analyzing table structure...')
      } else if (lastLog.message.includes('Starting export')) {
        setProgress(85)
        setProgressMessage('Generating Excel and CSV files...')
      } else if (lastLog.message.includes('Conversion completed successfully')) {
        setProgress(100)
        setProgressMessage('Complete!')
      }
    }
  }, [debugLogs, isProcessing])

  return (
    <>
      <Head>
        <title>Bank Statement Converter - Debug Mode</title>
        <meta name="description" content="Convert bank statement PDFs to Excel and CSV format" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          {/* Header with Debug Toggle */}
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Bank Statement Converter
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-4">
              Convert your UK bank statement PDFs into structured Excel and CSV files.
            </p>
            
            {/* Debug Controls */}
            <div className="flex justify-center items-center gap-4 mt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={debugMode}
                  onChange={(e) => setDebugMode(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">Debug Mode</span>
              </label>
              
              {debugLogs.length > 0 && (
                <button
                  onClick={() => setShowDebugPanel(!showDebugPanel)}
                  className="px-4 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  {showDebugPanel ? 'Hide' : 'Show'} Debug Panel ({debugLogs.length} logs)
                </button>
              )}
              
              <button
                onClick={checkApiHealth}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Check API Health
              </button>
            </div>
            
            {/* API Health Status */}
            {apiHealth && (
              <div className={`mt-4 p-2 rounded-lg text-sm ${
                apiHealth.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                API Status: {apiHealth.status}
                {apiHealth.system && (
                  <span className="ml-2">
                    | Tesseract: {apiHealth.system.tesseract}
                    | Memory: {apiHealth.system.memory_percent}%
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Debug Panel */}
          {showDebugPanel && (debugLogs.length > 0 || errorDetails) && (
            <DebugPanel
              logs={debugLogs}
              errorDetails={errorDetails}
              result={result}
              onClose={() => setShowDebugPanel(false)}
            />
          )}

          {/* Main Content */}
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12">
              {!result && !isProcessing && (
                <div className="space-y-8">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                      Upload Your Bank Statement
                    </h2>
                    <p className="text-gray-600">
                      Drop your PDF file here or click to browse
                    </p>
                  </div>

                  <FileUpload onFileUpload={handleFileUpload} />
                </div>
              )}

              {isProcessing && (
                <div className="text-center space-y-6">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                    <svg className="animate-spin w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                      Processing Your Statement
                    </h2>
                    <p className="text-gray-600 mb-2">
                      {progressMessage || 'Extracting and parsing your transaction data...'}
                    </p>
                    
                    {/* Show current processing step from logs */}
                    {debugMode && debugLogs.length > 0 && (
                      <div className="text-xs text-gray-500 mt-2 p-2 bg-gray-50 rounded">
                        Last action: {debugLogs[debugLogs.length - 1].message}
                      </div>
                    )}
                    
                    <ProgressBar progress={progress} />
                  </div>
                </div>
              )}

              {result && result.success && (
                <div className="text-center space-y-6">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                      Conversion Complete!
                    </h2>
                    <p className="text-gray-600 mb-2">
                      Successfully processed {result.transactions_count} transactions
                    </p>
                    {result.processing_time && (
                      <p className="text-sm text-gray-500">
                        Processing time: {result.processing_time}s
                      </p>
                    )}
                    
                    <div className="space-y-4 mt-6">
                      <DownloadLink
                        url={result.excel_url}
                        filename="bank_transactions.xlsx"
                        type="excel"
                      />
                      <DownloadLink
                        url={result.csv_url}
                        filename="bank_transactions.csv"
                        type="csv"
                      />
                    </div>
                    
                    <button
                      onClick={resetForm}
                      className="mt-8 px-6 py-2 text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      Convert Another File
                    </button>
                  </div>
                </div>
              )}

              {error && (
                <div className="text-center space-y-6">
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                      Conversion Failed
                    </h2>
                    <p className="text-red-600 mb-6">
                      {error}
                    </p>
                    
                    {errorDetails && debugMode && (
                      <div className="text-left bg-red-50 p-4 rounded-lg mb-4">
                        <p className="text-sm font-medium text-red-900 mb-2">Error Details:</p>
                        <pre className="text-xs text-red-700 overflow-x-auto">
                          {JSON.stringify({
                            session_id: errorDetails.session_id,
                            has_raw_content: !!errorDetails.raw_content,
                            logs_count: errorDetails.debug_logs?.length || 0
                          }, null, 2)}
                        </pre>
                      </div>
                    )}
                    
                    <button
                      onClick={resetForm}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  )
}