import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { PricePrediction } from './types'

export function usePricePrediction(symbol: string | null) {
  return useQuery<PricePrediction>({
    queryKey: ['onchain-prediction', symbol],
    queryFn: () =>
      apiClient.get(`/onchain-prediction/${symbol}`).then((r) => r.data.data),
    enabled: !!symbol,
    staleTime: 4 * 60 * 1000, // treat as fresh for 4 min (cache TTL is 5 min)
    retry: 1,
  })
}

export function useRefreshPrediction(symbol: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient.post(`/onchain-prediction/${symbol}/refresh`).then((r) => r.data.data),
    onSuccess: (data) => {
      qc.setQueryData(['onchain-prediction', symbol], data)
    },
  })
}
