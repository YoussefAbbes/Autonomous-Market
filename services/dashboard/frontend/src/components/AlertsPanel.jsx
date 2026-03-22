import { AlertTriangle, AlertCircle, Info, TrendingUp, TrendingDown, Frown, Smile, Clock, Bell } from 'lucide-react'

function AlertsPanel({ alerts, darkMode, cardBg }) {
  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'critical':
        return { bg: 'bg-red-900/50', text: 'text-red-400', Icon: AlertTriangle }
      case 'warning':
        return { bg: 'bg-yellow-900/50', text: 'text-yellow-400', Icon: AlertCircle }
      case 'info':
      default:
        return { bg: 'bg-blue-900/50', text: 'text-blue-400', Icon: Info }
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'price_spike':
        return TrendingUp
      case 'price_drop':
        return TrendingDown
      case 'sentiment_crash':
        return Frown
      case 'sentiment_surge':
        return Smile
      case 'data_stale':
        return Clock
      default:
        return Bell
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

  if (!alerts || alerts.length === 0) {
    return (
      <div className={`${cardBg} rounded-lg p-8 text-center`}>
        <Bell className={`mx-auto mb-4 ${darkMode ? 'text-gray-600' : 'text-gray-400'}`} size={48} />
        <div className={`text-lg ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          No alerts yet
        </div>
        <div className={`text-sm mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          Alerts will appear here when significant price changes occur
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Recent Alerts ({alerts.length})</h2>

      <div className="space-y-3">
        {alerts.map((alert, i) => {
          const style = getSeverityStyle(alert.severity)
          const TypeIconComponent = getTypeIcon(alert.type)

          return (
            <div
              key={i}
              className={`${cardBg} rounded-lg p-4 border-l-4 ${
                alert.severity === 'critical'
                  ? 'border-red-500'
                  : alert.severity === 'warning'
                  ? 'border-yellow-500'
                  : 'border-blue-500'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-full ${style.bg}`}>
                  <TypeIconComponent className={style.text} size={20} />
                </div>
                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded ${style.bg} ${style.text} font-medium`}>
                      <style.Icon size={12} />
                      {alert.severity?.toUpperCase()}
                    </span>
                    <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                      {alert.type?.replace('_', ' ')}
                    </span>
                    {alert.symbol && (
                      <span className={`text-xs font-mono font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {alert.symbol}
                      </span>
                    )}
                  </div>
                  <div className="font-medium">{alert.message}</div>
                  <div className={`text-xs mt-2 flex items-center gap-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    <Clock size={12} />
                    {formatTime(alert.created_at)}
                  </div>
                </div>
              </div>

              {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                <div className={`mt-3 pt-3 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                    {alert.metadata.current_price && (
                      <div>
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>Current: </span>
                        <span className="font-medium">${alert.metadata.current_price.toLocaleString()}</span>
                      </div>
                    )}
                    {alert.metadata.prev_price && (
                      <div>
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>Previous: </span>
                        <span className="font-medium">${alert.metadata.prev_price.toLocaleString()}</span>
                      </div>
                    )}
                    {alert.metadata.change_pct && (
                      <div>
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>Change: </span>
                        <span className={`font-medium flex items-center gap-1 ${alert.metadata.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {alert.metadata.change_pct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                          {alert.metadata.change_pct >= 0 ? '+' : ''}{alert.metadata.change_pct.toFixed(2)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AlertsPanel
