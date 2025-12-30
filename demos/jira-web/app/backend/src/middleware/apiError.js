export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  static badRequest(message, details) {
    return new ApiError(400, 'validation_error', message, details);
  }

  static unauthorized(message = 'Unauthorized') {
    return new ApiError(401, 'unauthorized', message);
  }

  static forbidden(message = 'Forbidden') {
    return new ApiError(403, 'forbidden', message);
  }

  static notFound(message = 'Not found', details) {
    return new ApiError(404, 'not_found', message, details ?? null);
  }

  static serviceUnavailable(message = 'Service unavailable', details) {
    return new ApiError(503, 'service_unavailable', message, details ?? null);
  }
}
