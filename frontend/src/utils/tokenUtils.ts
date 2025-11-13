interface DecodedToken {
  exp: number
  sub: string
  iat?: number
  jti?: string
}

function base64UrlDecode(str: string): string {
  // Replace URL-safe characters with standard base64 characters
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  
  // Pad the string to a multiple of 4
  while (base64.length % 4) {
    base64 += '='
  }
  
  return base64
}

export function decodeToken(token: string): DecodedToken | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }

    // Decode base64url payload correctly
    const base64Url = parts[1]
    const base64 = base64UrlDecode(base64Url)
    const payload = JSON.parse(atob(base64))
    
    return {
      exp: payload.exp,
      sub: payload.sub,
      iat: payload.iat,
      jti: payload.jti,
    }
  } catch (error) {
    console.warn('Failed to decode token:', error)
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const decoded = decodeToken(token)
  if (!decoded) {
    return true
  }

  const now = Math.floor(Date.now() / 1000)
  return decoded.exp < now
}

export function getTokenExpirationTime(token: string): number | null {
  const decoded = decodeToken(token)
  return decoded?.exp ?? null
}

export function getTimeUntilExpiration(token: string): number {
  const exp = getTokenExpirationTime(token)
  if (!exp) {
    return 0
  }

  const now = Date.now()
  const expMs = exp * 1000
  return Math.max(0, expMs - now)
}

export function shouldRefreshToken(token: string, bufferMinutes: number = 5): boolean {
  const timeUntil = getTimeUntilExpiration(token)
  const bufferMs = bufferMinutes * 60 * 1000
  return timeUntil < bufferMs && timeUntil > 0
}

