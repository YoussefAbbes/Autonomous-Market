import { useState, useEffect, createContext, useContext } from 'react'
import axios from 'axios'
import { TrendingUp, RefreshCw, Sun, Moon } from 'lucide-react'
import MetricsCards from './components/MetricsCards'
import PriceChart from './components/PriceChart'
import SentimentGauge from './components/SentimentGauge'
import NewsFeed from './components/NewsFeed'
import CoinSelector from './components/CoinSelector'
import AlertsPanel from './components/AlertsPanel'

const API_BASE = '/api'

// Theme context for dark/light mode
export const ThemeContext = createContext()

// Currency context
export const CurrencyContext = createContext()

const CURRENCIES = [
  { code: 'usd', symbol: '$', name: 'US Dollar' },
  { code: 'eur', symbol: '€', name: 'Euro' },
  { code: 'gbp', symbol: '£', name: 'British Pound' },
  { code: 'jpy', symbol: '¥', name: 'Japanese Yen' }
]

const TIMEFRAMES = [
  { value: 1, label: '1H' },
  { value: 24, label: '24H' },
  { value: 168, label: '7D' },
  { value: 720, label: '30D' }
]

function App() {
  // State
  const [summary, setSummary] = useState(null)
  const [prices, setPrices] = useState(null)
  const [news, setNews] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [coins, setCoins] = useState(null)
  const [forecasts, setForecasts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  // User preferences
  const [darkMode, setDarkMode] = useState(true)
  const [currency, setCurrency] = useState('usd')
  const [timeframe, setTimeframe] = useState(24)
  const [selectedCoins, setSelectedCoins] = useState([])
  const [newsSearch, setNewsSearch] = useState('')
  const [sentimentFilter, setSentimentFilter] = useState('')
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showForecasts, setShowForecasts] = useState(true)

  const currencySymbol = CURRENCIES.find(c => c.code === currency)?.symbol || '$'

  const fetchData = async () => {
    try {
      const [summaryRes, pricesRes, newsRes, alertsRes, coinsRes] = await Promise.all([
        axios.get(`${API_BASE}/summary?currency=${currency}`),
        axios.get(`${API_BASE}/prices?hours=${timeframe}&currency=${currency}`),
        axios.get(`${API_BASE}/news?limit=20${newsSearch ? `&search=${newsSearch}` : ''}${sentimentFilter ? `&sentiment_filter=${sentimentFilter}` : ''}`),
        axios.get(`${API_BASE}/alerts?limit=10`),
        axios.get(`${API_BASE}/coins`)
      ])

      setSummary(summaryRes.data)
      setPrices(pricesRes.data)
      setNews(newsRes.data)
      setAlerts(alertsRes.data)
      setCoins(coinsRes.data)
      setLastUpdate(new Date())
      setError(null)

      // Fetch forecasts for Bitcoin (main coin)
      try {
        const forecastRes = await axios.get(`${API_BASE}/forecast/bitcoin?horizon_hours=24`)
        if (forecastRes.data && !forecastRes.data.error) {
          setForecasts(prev => ({ ...prev, bitcoin: forecastRes.data }))
        }
      } catch (err) {
        console.log('Forecast not available:', err.message)
      }
    } catch (err) {
      console.error('Failed to fetch data:', err)
      setError('Failed to connect to API. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [currency, timeframe, newsSearch, sentimentFilter])

  const bgColor = darkMode ? 'bg-gray-900' : 'bg-gray-100'
  const textColor = darkMode ? 'text-white' : 'text-gray-900'
  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white'
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200'

  if (loading) {
    return (
      <div className={`min-h-screen ${bgColor} flex items-center justify-center`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className={`${textColor} text-xl`}>Loading market data...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`min-h-screen ${bgColor} flex items-center justify-center`}>
        <div className="text-center">
          <div className="text-red-400 text-xl mb-4">{error}</div>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <ThemeContext.Provider value={{ darkMode, setDarkMode }}>
      <CurrencyContext.Provider value={{ currency, setCurrency, currencySymbol }}>
        <div className={`min-h-screen ${bgColor} ${textColor}`}>
          {/* Header */}
          <header className={`${cardBg} border-b ${borderColor} px-4 md:px-6 py-4`}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                  <TrendingUp className="text-white" size={24} />
                </div>
                <h1 className="text-xl md:text-2xl font-bold">Market Intelligence</h1>
              </div>

              <div className="flex flex-wrap items-center gap-2 md:gap-4">
                {/* Currency Selector */}
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className={`px-3 py-1.5 rounded ${darkMode ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-900'} text-sm font-medium`}
                >
                  {CURRENCIES.map(c => (
                    <option key={c.code} value={c.code}>
                      {c.symbol} {c.code.toUpperCase()}
                    </option>
                  ))}
                </select>

                {/* Timeframe Selector */}
                <div className="flex rounded overflow-hidden">
                  {TIMEFRAMES.map(tf => (
                    <button
                      key={tf.value}
                      onClick={() => setTimeframe(tf.value)}
                      className={`px-3 py-1.5 text-sm font-medium ${
                        timeframe === tf.value
                          ? 'bg-blue-600 text-white'
                          : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {tf.label}
                    </button>
                  ))}
                </div>

                {/* Dark/Light Mode Toggle */}
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className={`p-2 rounded ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} transition-colors`}
                  title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                >
                  {darkMode ? <Sun size={18} /> : <Moon size={18} />}
                </button>

                {/* Refresh Button */}
                <button
                  onClick={fetchData}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  <RefreshCw size={14} />
                  Refresh
                </button>
              </div>
            </div>

            {/* Last Updated */}
            <div className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Last updated: {lastUpdate?.toLocaleTimeString()}
            </div>
          </header>

          {/* Navigation Tabs */}
          <nav className={`${cardBg} border-b ${borderColor} px-4 md:px-6`}>
            <div className="flex gap-4 overflow-x-auto">
              {['dashboard', 'coins', 'news', 'alerts'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-3 px-2 border-b-2 capitalize whitespace-nowrap ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-500'
                      : `border-transparent ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </nav>

          <main className="p-4 md:p-6">
            {activeTab === 'dashboard' && (
              <>
                {/* Metrics Cards */}
                <MetricsCards
                  summary={summary}
                  darkMode={darkMode}
                  currencySymbol={currencySymbol}
                />

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mt-6">
                  {/* Price Chart */}
                  <div className={`lg:col-span-2 ${cardBg} rounded-xl p-4 backdrop-blur-sm bg-opacity-90 border ${darkMode ? 'border-gray-700' : 'border-gray-200'} shadow-xl`}>
                    <div className="flex justify-between items-center mb-4">
                      <h2 className="text-lg font-semibold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        Price Trends ({TIMEFRAMES.find(t => t.value === timeframe)?.label})
                      </h2>
                      <button
                        onClick={() => setShowForecasts(!showForecasts)}
                        className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-300 ${
                          showForecasts
                            ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                            : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        {showForecasts ? '🔮 Forecasts ON' : '📊 Forecasts OFF'}
                      </button>
                    </div>
                    <PriceChart
                      data={prices}
                      darkMode={darkMode}
                      currencySymbol={currencySymbol}
                      selectedCoins={selectedCoins}
                      forecasts={forecasts}
                      showForecasts={showForecasts}
                    />
                  </div>

                  {/* Right Column */}
                  <div className="space-y-4 md:space-y-6">
                    {/* Sentiment Gauge */}
                    <div className={`${cardBg} rounded-xl p-4 backdrop-blur-sm bg-opacity-90 border ${darkMode ? 'border-gray-700' : 'border-gray-200'} shadow-xl hover:shadow-2xl transition-all duration-300`}>
                      <h2 className="text-lg font-semibold mb-4 bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">Market Sentiment</h2>
                      <SentimentGauge sentiment={summary?.sentiment} darkMode={darkMode} />
                    </div>

                    {/* Quick Stats */}
                    <div className={`${cardBg} rounded-xl p-4 backdrop-blur-sm bg-opacity-90 border ${darkMode ? 'border-gray-700' : 'border-gray-200'} shadow-xl hover:shadow-2xl transition-all duration-300`}>
                      <h2 className="text-lg font-semibold mb-4 bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">Quick Stats</h2>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className={darkMode ? 'text-gray-400' : 'text-gray-500'}>Coins Tracked</span>
                          <span className="font-medium">{coins?.count || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={darkMode ? 'text-gray-400' : 'text-gray-500'}>News Articles (24h)</span>
                          <span className="font-medium">{summary?.sentiment?.article_count || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={darkMode ? 'text-gray-400' : 'text-gray-500'}>Data Freshness</span>
                          <span className="font-medium">
                            {summary?.freshness?.minutes_since_price
                              ? `${Math.round(summary.freshness.minutes_since_price)} min`
                              : '--'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* News Preview */}
                <div className={`mt-6 ${cardBg} rounded-lg p-4`}>
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold">Latest News</h2>
                    <button
                      onClick={() => setActiveTab('news')}
                      className="text-blue-500 hover:text-blue-400 text-sm"
                    >
                      View All →
                    </button>
                  </div>
                  <NewsFeed
                    articles={news?.articles?.slice(0, 5)}
                    darkMode={darkMode}
                    compact={true}
                  />
                </div>
              </>
            )}

            {activeTab === 'coins' && (
              <CoinSelector
                coins={coins?.coins || []}
                prices={prices}
                darkMode={darkMode}
                cardBg={cardBg}
                currencySymbol={currencySymbol}
                selectedCoins={selectedCoins}
                setSelectedCoins={setSelectedCoins}
              />
            )}

            {activeTab === 'news' && (
              <div className={`${cardBg} rounded-lg p-4`}>
                <div className="flex flex-col md:flex-row gap-4 mb-4">
                  <input
                    type="text"
                    placeholder="Search news..."
                    value={newsSearch}
                    onChange={(e) => setNewsSearch(e.target.value)}
                    className={`flex-grow px-4 py-2 rounded ${
                      darkMode ? 'bg-gray-700 text-white placeholder-gray-400' : 'bg-gray-100 text-gray-900 placeholder-gray-500'
                    }`}
                  />
                  <select
                    value={sentimentFilter}
                    onChange={(e) => setSentimentFilter(e.target.value)}
                    className={`px-4 py-2 rounded ${
                      darkMode ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <option value="">All Sentiment</option>
                    <option value="positive">Positive</option>
                    <option value="neutral">Neutral</option>
                    <option value="negative">Negative</option>
                  </select>
                </div>
                <NewsFeed articles={news?.articles} darkMode={darkMode} />
              </div>
            )}

            {activeTab === 'alerts' && (
              <AlertsPanel alerts={alerts?.alerts || []} darkMode={darkMode} cardBg={cardBg} />
            )}
          </main>

          {/* Footer */}
          <footer className={`${cardBg} border-t ${borderColor} px-6 py-3 text-center text-sm ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
            Autonomous Market Intelligence System • {new Date().getFullYear()}
          </footer>
        </div>
      </CurrencyContext.Provider>
    </ThemeContext.Provider>
  )
}

export default App
