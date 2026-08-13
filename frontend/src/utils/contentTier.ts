const TIER_COLORS: Record<string, string> = {
  select: '#4f88b8',
  deluxe: '#268e7d',
  premium: '#b84e7e',
  ultra: '#aa7e18',
  exclusive: '#c46432',
};

export function getContentTierColor(tierName: string, apiColor: string): string {
  const key = tierName.toLowerCase().replace(/\s*edition$/i, '');
  const normalizedApiColor = apiColor.replace('#', '').slice(0, 6);
  return TIER_COLORS[key]
    ?? (/^[0-9a-f]{6}$/i.test(normalizedApiColor) ? `#${normalizedApiColor}` : '#6f756f');
}
