import { TrendingUp, TrendingDown, Activity, Clock, Coins, DollarSign } from 'lucide-react'
import CoinLogo from './CoinLogo'

function MetricsCards({ summary, darkMode, currencySymbol = '$' }) {
  if (!summary) return null

  const { latest_prices, price_changes, sentiment, freshness } = summary

  const formatPrice = (price) => {
    if (!price) return `${currencySymbol}0`
    if (price >= 1000) {
      return `${currencySymbol}${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    }
    if (price >= 1) {
      return `${currencySymbol}${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    return `${currencySymbol}${price.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 6 })}`
  }

  const formatChange = (change) => {
    if (!change && change !== 0) return '--'
    const sign = change >= 0 ? '+' : ''
    return `${sign}${change.toFixed(2)}%`
  }

  const formatMarketCap = (cap) => {
    if (!cap) return null
    if (cap >= 1e12) return `${currencySymbol}${(cap / 1e12).toFixed(1)}T`
    if (cap >= 1e9) return `${currencySymbol}${(cap / 1e9).toFixed(1)}B`
    if (cap >= 1e6) return `${currencySymbol}${(cap / 1e6).toFixed(1)}M`
    return `${currencySymbol}${cap.toLocaleString()}`
  }

  // Get top coins by market cap or price
  const getTopCoins = () => {
    if (!latest_prices || latest_prices.length === 0) return []

    // Sort by market cap if available, otherwise by price
    const sorted = [...latest_prices].sort((a, b) => {
      if (a.market_cap && b.market_cap) return b.market_cap - a.market_cap
      return b.price - a.price
    })

    return sorted.slice(0, 6).map(coin => {
      const change = price_changes?.find(p =>
        p.symbol?.toUpperCase() === coin.symbol?.toUpperCase()
      )

      return {
        symbol: coin.symbol,
        name: formatCoinName(coin.symbol),
        price: coin.price,
        change: change?.change_pct || coin.change_24h || 0,
        marketCap: coin.market_cap,
        volume: coin.volume
      }
    })
  }

  const formatCoinName = (symbol) => {
    const names = {
      'BITCOIN': 'Bitcoin',
      'ETHEREUM': 'Ethereum',
      'BINANCECOIN': 'BNB',
      'RIPPLE': 'XRP',
      'CARDANO': 'Cardano',
      'SOLANA': 'Solana',
      'POLKADOT': 'Polkadot',
      'DOGECOIN': 'Dogecoin',
      'AVALANCHE-2': 'Avalanche',
      'CHAINLINK': 'Chainlink'
    }
    return names[symbol?.toUpperCase()] || symbol?.replace('-', ' ')
  }

  const topCoins = getTopCoins()
  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white shadow'
  const glassCard = darkMode
    ? 'bg-gray-800/90 backdrop-blur-sm border border-gray-700'
    : 'bg-white/90 backdrop-blur-sm border border-gray-200 shadow-lg'
  const textMuted = darkMode ? 'text-gray-400' : 'text-gray-500'
  const textSubtle = darkMode ? 'text-gray-500' : 'text-gray-400'

  return (
    <div className="space-y-4">
      {/* Top Coins Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {topCoins.map((coin, i) => (
          <div key={i} className={`${glassCard} rounded-xl p-3 hover:ring-2 hover:ring-blue-500/50 hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:scale-[1.02]`}>
            <div className="flex items-center gap-2 mb-2">
              <CoinLogo symbol={coin.symbol} size="sm" />
              <div className={`${textMuted} text-xs font-medium uppercase`}>{coin.name}</div>
            </div>
            <div className="text-lg font-bold">{formatPrice(coin.price)}</div>
            <div className="flex items-center justify-between mt-1">
              <div className={`flex items-center gap-1 text-xs font-medium ${coin.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {coin.change >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {formatChange(coin.change)}
              </div>
              {coin.marketCap ? (
                <div className={`text-xs ${textSubtle}`}>
                  {formatMarketCap(coin.marketCap)}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Sentiment */}
        <div className={`${glassCard} rounded-xl p-3 hover:shadow-xl transition-all duration-300`}>
          <div className="flex items-center gap-2 mb-1">
            <Activity className={`${textMuted}`} size={14} />
            <div className={`${textMuted} text-xs font-medium`}>24H SENTIMENT</div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-lg font-bold ${
              sentiment?.average > 0.1 ? 'text-green-400' :
              sentiment?.average < -0.1 ? 'text-red-400' : ''
            }`}>
              {sentiment?.average?.toFixed(2) || '0.00'}
            </span>
            <span className={`text-xs ${textSubtle}`}>
              {sentiment?.article_count || 0} articles
            </span>
          </div>
        </div>

        {/* Data Freshness */}
        <div className={`${glassCard} rounded-xl p-3 hover:shadow-xl transition-all duration-300`}>
          <div className="flex items-center gap-2 mb-1">
            <Clock className={`${textMuted}`} size={14} />
            <div className={`${textMuted} text-xs font-medium`}>LAST UPDATE</div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-lg font-bold ${
              freshness?.minutes_since_price > 120 ? 'text-red-400' :
              freshness?.minutes_since_price > 60 ? 'text-yellow-400' : 'text-green-400'
            }`}>
              {freshness?.minutes_since_price
                ? `${Math.round(freshness.minutes_since_price)}m`
                : '--'}
            </span>
            <span className={`text-xs ${textSubtle}`}>ago</span>
          </div>
        </div>

        {/* Total Coins */}
        <div className={`${glassCard} rounded-xl p-3 hover:shadow-xl transition-all duration-300`}>
          <div className="flex items-center gap-2 mb-1">
            <Coins className={`${textMuted}`} size={14} />
            <div className={`${textMuted} text-xs font-medium`}>TRACKING</div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold">{latest_prices?.length || 0}</span>
            <span className={`text-xs ${textSubtle}`}>coins</span>
          </div>
        </div>

        {/* Currency */}
        <div className={`${glassCard} rounded-xl p-3 hover:shadow-xl transition-all duration-300`}>
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className={`${textMuted}`} size={14} />
            <div className={`${textMuted} text-xs font-medium`}>CURRENCY</div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold">{summary?.currency?.toUpperCase() || 'USD'}</span>
            <span className={`text-xs ${textSubtle}`}>{currencySymbol}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MetricsCards
