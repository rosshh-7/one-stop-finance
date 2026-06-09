export type FeatureTier = 'free' | 'pro'

export const FEATURE_FLAGS: Record<string, FeatureTier> = {
  theme_intelligence: 'free',
  options_chain: 'free',
  insider_trades: 'free',
  sentiment_analysis: 'free',
  trend_reversal: 'free',
  onchain_prediction: 'free',
} as const

export type FeatureName = keyof typeof FEATURE_FLAGS

export function getRequiredTier(feature: FeatureName): FeatureTier {
  return FEATURE_FLAGS[feature] ?? 'pro'
}

export function isFeatureAvailable(feature: FeatureName, userTier: FeatureTier): boolean {
  const required = getRequiredTier(feature)
  if (required === 'free') return true
  return userTier === 'pro'
}
