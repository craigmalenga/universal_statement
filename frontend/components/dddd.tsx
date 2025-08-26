// frontend/components/ProgressBar.tsx
interface ProgressBarProps {
  progress: number
}

export default function ProgressBar({ progress }: ProgressBarProps) {
  const getProgressStage = (progress: number) => {
    if (progress < 20) return 'Uploading file...'
    if (progress < 40) return 'Analyzing document structure...'
    if (progress < 60) return 'Extracting text content...'
    if (progress < 80) return 'Parsing transaction data...'
    if (progress < 95) return 'Generating output files...'
    return 'Almost done...'
  }

  const getProgressColor = (progress: number) => {
    if (progress < 30) return 'bg-blue-500'
    if (progress < 60) return 'bg-indigo-500'
    if (progress < 90) return 'bg-purple-500'
    return 'bg-green-500'
  }

  return (
    <div className="w-full max-w-md mx-auto space-y-4">
      {/* Progress Bar */}
      <div className="relative">
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${getProgressColor(progress)}`}
            style={{ width: `${Math.max(progress, 5)}%` }}
          >
            <div className="h-full bg-gradient-to-r from-white/20 to-transparent animate-pulse"></div>
          </div>
        </div>
        
        {/* Progress Percentage */}
        <div className="absolute top-0 right-0 -mt-6">
          <span className="text-sm font-medium text-gray-600">
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {/* Progress Stage */}
      <div className="text-center">
        <p className="text-sm font-medium text-gray-700 animate-pulse">
          {getProgressStage(progress)}
        </p>
      </div>

      {/* Progress Steps Indicator */}
      <div className="flex justify-between items-center mt-6">
        {[
          { step: 1, label: 'Upload', threshold: 20 },
          { step: 2, label: 'Extract', threshold: 50 },
          { step: 3, label: 'Parse', threshold: 75 },
          { step: 4, label: 'Export', threshold: 100 }
        ].map(({ step, label, threshold }) => (
          <div key={step} className="flex flex-col items-center space-y-2">
            <div
              className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                transition-all duration-300
                ${progress >= threshold
                  ? 'bg-green-500 text-white shadow-lg scale-110'
                  : progress >= threshold - 20
                  ? `${getProgressColor(progress)} text-white animate-pulse`
                  : 'bg-gray-200 text-gray-500'
                }
              `}
            >
              {progress >= threshold ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                step
              )}
            </div>
            <span
              className={`
                text-xs font-medium transition-colors
                ${progress >= threshold ? 'text-green-600' : 'text-gray-500'}
              `}
            >
              {label}
            </span>
          </div>
        ))}
      </div>

      {/* Animated Dots for Active Processing */}
      {progress < 100 && (
        <div className="flex justify-center space-x-1 mt-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      )}
    </div>
  )
}