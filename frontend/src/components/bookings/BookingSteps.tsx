interface BookingStepsProps {
  currentStep: number
  steps?: string[]
}

const defaultSteps = ['Selection', 'Guest Details', 'Source & Payment', 'Review']

export default function BookingSteps({ currentStep, steps = defaultSteps }: BookingStepsProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {steps.map((label, idx) => {
          const stepNum = idx + 1
          const isActive = stepNum === currentStep
          const isCompleted = stepNum < currentStep
          return (
            <div key={label} className="flex-1 flex flex-col items-center relative">
              {idx > 0 && (
                <div
                  className={`absolute left-0 top-4 -translate-x-1/2 w-full h-0.5 ${
                    isCompleted || isActive ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  style={{ width: 'calc(100% - 2rem)', left: '-50%' }}
                />
              )}
              <div
                className={`z-10 flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium border-2 ${
                  isCompleted
                    ? 'bg-brand-600 border-brand-600 text-white'
                    : isActive
                      ? 'bg-white dark:bg-gray-800 border-brand-600 text-brand-600'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-400'
                }`}
              >
                {isCompleted ? (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stepNum
                )}
              </div>
              <span
                className={`mt-2 text-xs font-medium ${
                  isActive ? 'text-brand-600' : isCompleted ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400'
                }`}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
