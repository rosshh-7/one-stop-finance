import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { OptionsChain } from './types'

export function useOptionsChain(symbol: string | null, expiry?: string) {
  return useQuery<OptionsChain>({
    queryKey: ['options-chain', symbol, expiry],
    queryFn: () => {
      const params = expiry ? `?expiry=${expiry}` : ''
      return apiClient.get(`/options/${symbol}${params}`).then(r => r.data.data)
    },
    enabled: !!symbol,
    staleTime: 55_000,
    retry: 1,
  })
}
