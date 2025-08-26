// frontend/components/DebugPanel.tsx
import { useState } from 'react'

interface DebugPanelProps {
  logs: DebugLog[]
  errorDetails?: ErrorResponse | null
  result?: ConversionResult | null
  onClose: () => void
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

export default function DebugPanel({ logs, errorDetails, result, onClose }: DebugPanelProps) {
  const [activeTab, setActiveTab] = useState<'logs' | 'raw' | 'details' | 'transactions'>('logs')
  const [expandedLogIndex, setExpandedLogIndex] = useState<number | null>(null)

  const getLogColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'WARNING':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'SUCCESS':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'DEBUG':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    } catch {
      return timestamp
    }
  }

  const rawContent = errorDetails?.raw_content || result?.raw_content_preview || ''
  const hasRawContent = rawContent.length > 0

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Debug Panel
            {result?.session_id && (
              <span className="ml-2 text-sm text-gray-500">
                Session: {result.session_id.slice(0, 8)}...
              </span>
            )}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-gray-200 flex gap-4">
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'logs' 
                ? 'bg-blue-100 text-blue-700' 
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Logs ({logs.length})
          </button>
          
          {hasRawContent && (
            <button
              onClick={() => setActiveTab('raw')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'raw' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Raw Text
            </button>
          )}
          
          {(result?.extraction_details || result?.parsing_details) && (
            <button
              onClick={() => setActiveTab('details')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'details' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Processing Details
            </button>
          )}
          
          {result?.sample_transactions && result.sample_transactions.length > 0 && (
            <button
              onClick={() => setActiveTab('transactions')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'transactions' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Sample Data
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'logs' && (
            <div className="space-y-2">
              {logs.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No debug logs available</p>
              ) : (
                logs.map((log, index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-3 ${getLogColor(log.level)} cursor-pointer transition-all`}
                    onClick={() => setExpandedLogIndex(expandedLogIndex === index ? null : index)}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium uppercase">
                            {log.level}
                          </span>
                          <span className="text-xs opacity-75">
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>
                        <p className="mt-1 font-medium">
                          {log.message}
                        </p>
                      </div>
                      {log.data && (
                        <svg 
                          className={`w-4 h-4 transition-transform ${
                            expandedLogIndex === index ? 'rotate-180' : ''
                          }`} 
                          fill="none" 
                          stroke="currentColor" 
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      )}
                    </div>
                    
                    {log.data && expandedLogIndex === index && (
                      <div className="mt-3 pt-3 border-t border-current border-opacity-20">
                        <pre className="text-xs overflow-x-auto bg-white bg-opacity-50 rounded p-2">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'raw' && hasRawContent && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="font-medium text-gray-900">
                  Extracted Text Content ({rawContent.length} characters)
                </h3>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(rawContent)
                    alert('Copied to clipboard!')
                  }}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Copy to Clipboard
                </button>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                <pre className="whitespace-pre-wrap break-words">
                  {rawContent}
                </pre>
              </div>
              
              {errorDetails?.traceback && (
                <div className="mt-4">
                  <h4 className="font-medium text-red-700 mb-2">Error Traceback:</h4>
                  <div className="bg-red-50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                    <pre className="text-red-700">{errorDetails.traceback}</pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-6">
              {result?.extraction_details && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Extraction Details</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Method Used:</dt>
                        <dd className="text-sm font-medium">
                          {result.extraction_details.method || 'Unknown'}
                        </dd>
                      </div>
                      {result.extraction_details.pages_processed && (
                        <div className="flex justify-between">
                          <dt className="text-sm text-gray-600">Pages Processed:</dt>
                          <dd className="text-sm font-medium">
                            {result.extraction_details.pages_processed}
                          </dd>
                        </div>
                      )}
                      {result.extraction_details.text_extraction_result && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-sm font-medium text-gray-700 mb-2">Text Extraction Result:</p>
                          <pre className="text-xs bg-white rounded p-2">
                            {JSON.stringify(result.extraction_details.text_extraction_result, null, 2)}
                          </pre>
                        </div>
                      )}
                      {result.extraction_details.ocr_result && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-sm font-medium text-gray-700 mb-2">OCR Result:</p>
                          <pre className="text-xs bg-white rounded p-2">
                            {JSON.stringify(result.extraction_details.ocr_result, null, 2)}
                          </pre>
                        </div>
                      )}
                    </dl>
                  </div>
                </div>
              )}

              {result?.parsing_details && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Parsing Details</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Strategy Used:</dt>
                        <dd className="text-sm font-medium">
                          {result.parsing_details.strategy_used || 'None'}
                        </dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-sm text-gray-600">Strategies Tried:</dt>
                        <dd className="text-sm font-medium">
                          {result.parsing_details.strategies_tried?.join(', ') || 'None'}
                        </dd>
                      </div>
                      {result.parsing_details.transactions_per_strategy && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-sm font-medium text-gray-700 mb-2">Transactions Found Per Strategy:</p>
                          <div className="space-y-1">
                            {Object.entries(result.parsing_details.transactions_per_strategy).map(([strategy, count]) => (
                              <div key={strategy} className="flex justify-between text-xs">
                                <span className="text-gray-600">{strategy}:</span>
                                <span className="font-medium">{count as number}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </dl>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'transactions' && result?.sample_transactions && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-900">
                Sample Transactions (First {result.sample_transactions.length})
              </h3>
              
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Description
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Debit
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Credit
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Balance
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {result.sample_transactions.map((transaction, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {transaction.date}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {transaction.description}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                          {transaction.debit || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                          {transaction.credit || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                          {transaction.balance || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}