export class AppError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = new.target.name;
  }
}

export class InvalidRequestError extends AppError {
  constructor(message: string, details?: unknown) {
    super("invalid_request", message, 400, details);
  }
}

export class NotFoundError extends AppError {
  constructor(message = "The requested resource was not found.") {
    super("not_found", message, 404);
  }
}

export class ConflictError extends AppError {
  constructor(code: string, message: string, details?: unknown) {
    super(code, message, 409, details);
  }
}

export class UnprocessableError extends AppError {
  constructor(code: string, message: string, details?: unknown) {
    super(code, message, 422, details);
  }
}

export class UnauthorizedWebhookError extends AppError {
  constructor(message: string) {
    super("invalid_webhook_signature", message, 401);
  }
}

export class ProviderError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean,
    public readonly statusCode?: number
  ) {
    super(message);
    this.name = "ProviderError";
  }
}
