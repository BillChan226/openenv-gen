export function errorHandler(err, req, res, next) {
  console.error(err.stack)

  if (err.name === 'ValidationError') {
    return res.status(400).json({ message: err.message, errors: err.errors })
  }

  if (err.name === 'SequelizeUniqueConstraintError') {
    return res.status(409).json({ message: 'Resource already exists' })
  }

  res.status(err.status || 500).json({
    message: err.message || 'Internal server error',
  })
}
