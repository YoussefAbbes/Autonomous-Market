// Cryptocurrency logo component with fallback
const COIN_LOGOS = {
  'BITCOIN': 'https://assets.coingecko.com/coins/images/1/standard/bitcoin.png',
  'ETHEREUM': 'https://assets.coingecko.com/coins/images/279/standard/ethereum.png',
  'BINANCECOIN': 'https://assets.coingecko.com/coins/images/825/standard/bnb-icon2_2x.png',
  'RIPPLE': 'https://assets.coingecko.com/coins/images/44/standard/xrp-symbol-white-128.png',
  'CARDANO': 'https://assets.coingecko.com/coins/images/975/standard/cardano.png',
  'SOLANA': 'https://assets.coingecko.com/coins/images/4128/standard/solana.png',
  'POLKADOT': 'https://assets.coingecko.com/coins/images/12171/standard/polkadot.png',
  'DOGECOIN': 'https://assets.coingecko.com/coins/images/5/standard/dogecoin.png',
  'AVALANCHE-2': 'https://assets.coingecko.com/coins/images/12559/standard/Avalanche_Circle_RedWhite_Trans.png',
  'CHAINLINK': 'https://assets.coingecko.com/coins/images/877/standard/chainlink-new-logo.png'
}

function CoinLogo({ symbol, size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20'
  }

  const logoUrl = COIN_LOGOS[symbol?.toUpperCase()]

  if (!logoUrl) {
    // Fallback with first letter
    return (
      <div className={`${sizeClasses[size]} rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white ${className}`}>
        {symbol?.charAt(0) || '?'}
      </div>
    )
  }

  return (
    <img
      src={logoUrl}
      alt={symbol}
      className={`${sizeClasses[size]} rounded-full ${className}`}
      onError={(e) => {
        e.target.style.display = 'none'
        e.target.parentElement.innerHTML = `<div class="${sizeClasses[size]} rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white">${symbol?.charAt(0) || '?'}</div>`
      }}
    />
  )
}

export default CoinLogo
