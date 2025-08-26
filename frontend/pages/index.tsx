// frontend/pages/index.tsx
import { useState } from 'react'
import Head from 'next/head'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/dddd'
import DownloadLink from '../components/DownloadLink'

interface ConversionResult {
  session_id: string
  transactions_count: number
  excel_url: string
  csv_url: string
}

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<ConversionResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true)
    setProgress(0)
    setResult(null)
    setError(null)

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 500)

      const formData = new FormData()
      formData.append('file', file)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/convert`, {
        method: 'POST',
        body: formData,
      })

      clearInterval(progressInterval)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Conversion failed')
      }

      const data = await response.json()
      setProgress(100)
      setResult(data)

      // Auto-cleanup after 30 minutes
      setTimeout(() => {
        fetch(`${apiUrl}/cleanup/${data.session_id}`, { method: 'DELETE' })
      }, 30 * 60 * 1000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setProgress(0)
    } finally {
      setIsProcessing(false)
    }
  }

  const resetForm = () => {
    setResult(null)
    setError(null)
    setProgress(0)
  }

  return (
    <>
      <Head>
        <title>Bank Statement Converter</title>
        <meta name="description" content="Convert bank statement PDFs to Excel and CSV format" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Bank Statement Converter
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Convert your UK bank statement PDFs into structured Excel and CSV files. 
              Works with both digital and scanned documents.
            </p>
          </div>

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

                  {/* Features */}
                  <div className="grid md:grid-cols-3 gap-6 mt-12">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h3 className="font-semibold text-gray-900 mb-1">Smart Recognition</h3>
                      <p className="text-sm text-gray-600">Handles both digital and scanned PDFs with OCR fallback</p>
                    </div>

                    <div className="text-center">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <h3 className="font-semibold text-gray-900 mb-1">Multiple Formats</h3>
                      <p className="text-sm text-gray-600">Download as Excel (.xlsx) or CSV for easy analysis</p>
                    </div>

                    <div className="text-center">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                      </div>
                      <h3 className="font-semibold text-gray-900 mb-1">Secure Processing</h3>
                      <p className="text-sm text-gray-600">Files are processed securely and automatically deleted</p>
                    </div>
                  </div>
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
                    <p className="text-gray-600 mb-6">
                      Extracting and parsing your transaction data...
                    </p>
                    <ProgressBar progress={progress} />
                  </div>
                </div>
              )}

              {result && (
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
                    <p className="text-gray-600 mb-6">
                      Successfully processed {result.transactions_count} transactions
                    </p>
                    
                    <div className="space-y-4">
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

          {/* Footer */}
          <div className="text-center mt-12 text-gray-500 text-sm">
            <p>Supports major UK banks including Barclays, HSBC, NatWest, and more</p>
            <p className="mt-2">Files are automatically deleted after processing for your security</p>
          </div>
        </div>
      </main>
    </>
  )
}