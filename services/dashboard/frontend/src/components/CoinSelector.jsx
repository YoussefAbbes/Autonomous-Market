import { TrendingUp, TrendingDown, CheckCircle, BarChart3, Activity } from 'lucide-react'
import CoinLogo from './CoinLogo'

function CoinSelector({ coins, prices, darkMode, cardBg, currencySymbol, selectedCoins, setSelectedCoins }) {
  const formatPrice = (price) => {
    if (!price) return `${currencySymbol}0`
    if (price >= 1000) {
      return `${currencySymbol}${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    }
    return `${currencySymbol}${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
  }

  const formatMarketCap = (cap) => {
    if (!cap) return '--'
    if (cap >= 1e12) return `${currencySymbol}${(cap / 1e12).toFixed(2)}T`
    if (cap >= 1e9) return `${currencySymbol}${(cap / 1e9).toFixed(2)}B`
    if (cap >= 1e6) return `${currencySymbol}${(cap / 1e6).toFixed(2)}M`
    return `${currencySymbol}${cap.toLocaleString()}`
  }

  const formatVolume = (vol) => {
    if (!vol) return '--'
    if (vol >= 1e9) return `${currencySymbol}${(vol / 1e9).toFixed(2)}B`
    if (vol >= 1e6) return `${currencySymbol}${(vol / 1e6).toFixed(2)}M`
    if (vol >= 1e3) return `${currencySymbol}${(vol / 1e3).toFixed(2)}K`
    return `${currencySymbol}${vol.toFixed(2)}`
  }

  const toggleCoin = (symbol) => {
    if (selectedCoins.includes(symbol)) {
      setSelectedCoins(selectedCoins.filter(s => s !== symbol))
    } else {
      setSelectedCoins([...selectedCoins, symbol])
    }
  }

  // Sort coins by market cap
  const sortedCoins = [...coins].sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0))

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">All Coins ({coins.length})</h2>
        {selectedCoins.length > 0 && (
          <button
            onClick={() => setSelectedCoins([])}
            className="text-sm text-blue-500 hover:text-blue-400"
          >
            Clear Selection ({selectedCoins.length})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {sortedCoins.map((coin) => {
          const isSelected = selectedCoins.includes(coin.symbol)
          const changeColor = coin.change_24h >= 0 ? 'text-green-400' : 'text-red-400'

          return (
            <div
              key={coin.symbol}
              onClick={() => toggleCoin(coin.symbol)}
              className={`${cardBg} rounded-lg p-4 cursor-pointer transition-all ${
                isSelected
                  ? 'ring-2 ring-blue-500 shadow-lg shadow-blue-500/20'
                  : darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-3">
                  <CoinLogo symbol={coin.symbol} size="lg" />
                  <div>
                    <div className="font-bold text-lg">{coin.symbol}</div>
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {coin.name}
                    </div>
                  </div>
                </div>
                <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded font-medium ${
                  coin.change_24h >= 0
                    ? 'bg-green-900/50 text-green-400'
                    : 'bg-red-900/50 text-red-400'
                }`}>
                  {coin.change_24h >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(2) || 0}%
                </div>
              </div>

              <div className="text-2xl font-bold mb-3">
                {formatPrice(coin.price)}
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className={`flex items-center gap-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    <BarChart3 size={12} />
                    <span>Market Cap</span>
                  </div>
                  <div className="font-medium">{formatMarketCap(coin.market_cap)}</div>
                </div>
                <div>
                  <div className={`flex items-center gap-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    <Activity size={12} />
                    <span>24h Volume</span>
                  </div>
                  <div className="font-medium">{formatVolume(coin.volume)}</div>
                </div>
              </div>

              {isSelected && (
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <div className="text-xs text-blue-400 flex items-center gap-1 font-medium">
                    <CheckCircle size={14} /> Selected for chart
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

export default CoinSelector
