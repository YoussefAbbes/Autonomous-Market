import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = {
  BITCOIN: '#f7931a',
  ETHEREUM: '#627eea',
  SOLANA: '#9945ff',
  BINANCECOIN: '#f3ba2f',
  RIPPLE: '#23292f',
  CARDANO: '#0033ad',
  POLKADOT: '#e6007a',
  DOGECOIN: '#c2a633',
  'AVALANCHE-2': '#e84142',
  CHAINLINK: '#375bd2'
}

const DEFAULT_COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00C49F',
  '#FFBB28', '#FF8042', '#0088FE', '#00C49F', '#FFBB28'
]

function PriceChart({ data, darkMode = true, currencySymbol = '$', selectedCoins = [] }) {
  if (!data || !data.symbols || Object.keys(data.symbols).length === 0) {
    return (
      <div className={`text-center py-10 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        No price data available
      </div>
    )
  }

  const { symbols } = data

  // Filter symbols if selection is made
  const displaySymbols = selectedCoins.length > 0
    ? Object.fromEntries(
        Object.entries(symbols).filter(([symbol]) =>
          selectedCoins.includes(symbol)
        )
      )
    : symbols

  // If filtering resulted in no data, show all
  const finalSymbols = Object.keys(displaySymbols).length > 0 ? displaySymbols : symbols

  // Transform data for Recharts - create time-series with all symbols
  const timeMap = new Map()

  Object.entries(finalSymbols).forEach(([symbol, points]) => {
    points.forEach(point => {
      const time = new Date(point.timestamp).getTime()
      if (!timeMap.has(time)) {
        timeMap.set(time, { timestamp: time })
      }
      timeMap.get(time)[symbol] = point.price
    })
  })

  const chartData = Array.from(timeMap.values())
    .sort((a, b) => a.timestamp - b.timestamp)

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    const hours = data.hours || 24

    if (hours <= 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (hours <= 168) {
      return date.toLocaleDateString([], { weekday: 'short', hour: '2-digit' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const formatPrice = (value) => {
    if (!value) return `${currencySymbol}0`
    if (value >= 1000000) return `${currencySymbol}${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `${currencySymbol}${(value / 1000).toFixed(1)}k`
    if (value >= 1) return `${currencySymbol}${value.toFixed(2)}`
    return `${currencySymbol}${value.toFixed(4)}`
  }

  const getColor = (symbol, index) => {
    return COLORS[symbol.toUpperCase()] || DEFAULT_COLORS[index % DEFAULT_COLORS.length]
  }

  const bgColor = darkMode ? '#1f2937' : '#ffffff'
  const textColor = darkMode ? '#9ca3af' : '#6b7280'
  const gridColor = darkMode ? '#374151' : '#e5e7eb'

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTime}
          stroke={gridColor}
          tick={{ fill: textColor, fontSize: 11 }}
          tickLine={{ stroke: gridColor }}
          axisLine={{ stroke: gridColor }}
        />
        <YAxis
          tickFormatter={formatPrice}
          stroke={gridColor}
          tick={{ fill: textColor, fontSize: 11 }}
          tickLine={{ stroke: gridColor }}
          axisLine={{ stroke: gridColor }}
          width={70}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: bgColor,
            border: darkMode ? '1px solid #374151' : '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
          }}
          labelStyle={{ color: textColor }}
          labelFormatter={(label) => new Date(label).toLocaleString()}
          formatter={(value, name) => [
            `${currencySymbol}${value?.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
            formatCoinName(name)
          ]}
        />
        <Legend
          wrapperStyle={{ paddingTop: '10px' }}
          formatter={(value) => (
            <span style={{ color: textColor }}>{formatCoinName(value)}</span>
          )}
        />
        {Object.keys(finalSymbols).map((symbol, index) => (
          <Line
            key={symbol}
            type="monotone"
            dataKey={symbol}
            stroke={getColor(symbol, index)}
            strokeWidth={2}
            dot={false}
            name={symbol}
            connectNulls={true}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function formatCoinName(symbol) {
  const names = {
    'BITCOIN': 'BTC',
    'ETHEREUM': 'ETH',
    'BINANCECOIN': 'BNB',
    'RIPPLE': 'XRP',
    'CARDANO': 'ADA',
    'SOLANA': 'SOL',
    'POLKADOT': 'DOT',
    'DOGECOIN': 'DOGE',
    'AVALANCHE-2': 'AVAX',
    'CHAINLINK': 'LINK'
  }
  return names[symbol?.toUpperCase()] || symbol
}

export default PriceChart
