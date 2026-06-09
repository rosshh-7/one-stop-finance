export interface OptionContract {
  strike: number
  bid: number
  ask: number
  last: number
  volume: number
  open_interest: number
  implied_volatility: number
  delta: number | null
  gamma: number | null
  theta: number | null
  in_the_money: boolean
}

export interface OptionsChain {
  symbol: string
  expiry: string
  expiries: string[]
  underlying_price: number
  put_call_ratio: number
  max_pain: number
  calls: OptionContract[]
  puts: OptionContract[]
}
