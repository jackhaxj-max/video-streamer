export class AppError extends Error {
  constructor(message, status = 422, code = 'RESOLUTION_FAILED') {
    super(message);
    this.status = status;
    this.code = code;
  }
}
