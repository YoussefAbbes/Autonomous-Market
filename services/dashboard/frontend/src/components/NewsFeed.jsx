import { ExternalLink, Newspaper } from 'lucide-react'

function NewsFeed({ articles, darkMode = true, compact = false }) {
  if (!articles || articles.length === 0) {
    return (
      <div className={`text-center py-10 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        No news articles available
      </div>
    )
  }

  const getSentimentStyle = (sentiment) => {
    if (sentiment > 0.3) return {
      icon: '📈',
      color: 'text-green-400',
      bg: darkMode ? 'bg-green-900/50' : 'bg-green-100',
      label: 'Bullish'
    }
    if (sentiment > 0.1) return {
      icon: '↗',
      color: 'text-green-300',
      bg: darkMode ? 'bg-green-900/30' : 'bg-green-50',
      label: 'Slightly Positive'
    }
    if (sentiment < -0.3) return {
      icon: '📉',
      color: 'text-red-400',
      bg: darkMode ? 'bg-red-900/50' : 'bg-red-100',
      label: 'Bearish'
    }
    if (sentiment < -0.1) return {
      icon: '↘',
      color: 'text-red-300',
      bg: darkMode ? 'bg-red-900/30' : 'bg-red-50',
      label: 'Slightly Negative'
    }
    return {
      icon: '→',
      color: darkMode ? 'text-gray-400' : 'text-gray-500',
      bg: darkMode ? 'bg-gray-700/50' : 'bg-gray-100',
      label: 'Neutral'
    }
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const itemBg = darkMode ? 'bg-gray-700/50 hover:bg-gray-700' : 'bg-gray-50 hover:bg-gray-100'
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900'
  const textMuted = darkMode ? 'text-gray-400' : 'text-gray-500'

  return (
    <div className={`space-y-2 ${compact ? 'max-h-64' : 'max-h-[500px]'} overflow-y-auto`}>
      {articles.map((article, i) => {
        const style = getSentimentStyle(article.sentiment)

        return (
          <div
            key={i}
            className={`flex items-start gap-3 p-3 ${itemBg} rounded-lg transition`}
          >
            {/* Sentiment indicator */}
            {!compact && (
              <div className={`w-10 h-10 flex items-center justify-center rounded-full ${style.bg} flex-shrink-0`}>
                <span className="text-lg">{style.icon}</span>
              </div>
            )}

            {/* Content */}
            <div className="flex-grow min-w-0">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`${textPrimary} hover:text-blue-400 font-medium ${compact ? 'line-clamp-1 text-sm' : 'line-clamp-2'} flex items-start gap-1 group`}
              >
                <span className="flex-grow">{article.headline}</span>
                <ExternalLink size={14} className="flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
              </a>
              <div className={`flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-xs ${textMuted}`}>
                <span className="font-medium">{article.source || 'Unknown'}</span>
                <span>•</span>
                <span>{formatTime(article.timestamp)}</span>
                {!compact && (
                  <>
                    <span>•</span>
                    <span className={`${style.color} font-medium`}>
                      {article.sentiment >= 0 ? '+' : ''}{article.sentiment?.toFixed(2) || '0.00'}
                    </span>
                  </>
                )}
                {compact && (
                  <span className={`${style.color}`}>{style.icon}</span>
                )}
              </div>
            </div>

            {/* Sentiment badge - only in full view */}
            {!compact && (
              <div className={`hidden md:flex items-center px-2 py-1 rounded text-xs ${style.bg} ${style.color}`}>
                {style.label}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default NewsFeed
