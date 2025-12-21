import React from 'react'

/**
 * Avatar Component - User avatar with fallback initials
 *
 * Teaches agents about:
 * - Image loading with fallbacks
 * - Size variants
 * - Click interactions
 */
function Avatar({
  src,
  alt,
  name,
  size = 'md',
  onClick,
  testId
}) {
  const [imageError, setImageError] = React.useState(false)

  const sizeClasses = {
    xs: 'w-6 h-6 text-xs',
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-base',
    lg: 'w-12 h-12 text-lg',
    xl: 'w-16 h-16 text-xl',
  }

  const getInitials = (name) => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  }

  const baseClasses = `${sizeClasses[size]} rounded-full flex items-center justify-center font-medium ${
    onClick ? 'cursor-pointer hover:opacity-80' : ''
  }`

  if (!src || imageError) {
    // Fallback to initials
    return (
      <div
        className={`${baseClasses} bg-blue-500 text-white`}
        onClick={onClick}
        data-testid={testId}
      >
        {getInitials(name || alt)}
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt || name}
      onError={() => setImageError(true)}
      onClick={onClick}
      className={`${baseClasses} object-cover`}
      data-testid={testId}
    />
  )
}

export default Avatar
