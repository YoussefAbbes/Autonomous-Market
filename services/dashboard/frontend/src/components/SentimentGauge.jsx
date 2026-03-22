function SentimentGauge({ sentiment, darkMode = true }) {
  if (!sentiment) {
    return (
      <div className={`text-center py-10 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        No sentiment data
      </div>
    )
  }

  const { average, article_count } = sentiment
  const safeAverage = average || 0

  // Convert -1 to 1 scale to 0-100 for the gauge
  const percentage = ((safeAverage + 1) / 2) * 100

  // Determine color and label based on sentiment
  let color, strokeColor, label, emoji

  if (safeAverage > 0.3) {
    color = 'text-green-400'
    strokeColor = '#22c55e'
    label = 'Bullish'
    emoji = '😊'
  } else if (safeAverage > 0.1) {
    color = 'text-green-300'
    strokeColor = '#86efac'
    label = 'Slightly Bullish'
    emoji = '🙂'
  } else if (safeAverage < -0.3) {
    color = 'text-red-400'
    strokeColor = '#ef4444'
    label = 'Bearish'
    emoji = '😰'
  } else if (safeAverage < -0.1) {
    color = 'text-red-300'
    strokeColor = '#fca5a5'
    label = 'Slightly Bearish'
    emoji = '😕'
  } else {
    color = darkMode ? 'text-gray-400' : 'text-gray-500'
    strokeColor = '#6b7280'
    label = 'Neutral'
    emoji = '😐'
  }

  const bgStroke = darkMode ? '#374151' : '#e5e7eb'
  const textMuted = darkMode ? 'text-gray-400' : 'text-gray-500'
  const textSubtle = darkMode ? 'text-gray-500' : 'text-gray-400'

  return (
    <div className="flex flex-col items-center justify-center h-full py-4">
      {/* Circular gauge representation */}
      <div className="relative w-36 h-36 md:w-40 md:h-40">
        <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 160 160">
          {/* Background circle */}
          <circle
            cx="80"
            cy="80"
            r="70"
            stroke={bgStroke}
            strokeWidth="10"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx="80"
            cy="80"
            r="70"
            stroke={strokeColor}
            strokeWidth="10"
            fill="none"
            strokeDasharray={`${percentage * 4.4} 440`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.5s ease' }}
          />
        </svg>
        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl mb-1">{emoji}</span>
          <span className={`text-2xl md:text-3xl font-bold ${color}`}>
            {safeAverage >= 0 ? '+' : ''}{safeAverage.toFixed(2)}
          </span>
          <span className={`${textMuted} text-xs md:text-sm`}>{label}</span>
        </div>
      </div>

      {/* Article count */}
      <div className="mt-4 text-center">
        <div className={`${textMuted} text-xs`}>Based on</div>
        <div className="text-lg md:text-xl font-semibold">{article_count || 0} articles</div>
        <div className={`${textSubtle} text-xs`}>in last 24 hours</div>
      </div>

      {/* Sentiment scale legend */}
      <div className="mt-4 flex items-center gap-2 text-xs">
        <span className="text-red-400">-1</span>
        <div className="w-16 md:w-20 h-2 bg-gradient-to-r from-red-500 via-gray-500 to-green-500 rounded"></div>
        <span className="text-green-400">+1</span>
      </div>
    </div>
  )
}

export default SentimentGauge
