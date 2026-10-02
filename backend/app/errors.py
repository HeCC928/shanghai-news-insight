class AppError(Exception):
    def __init__(self, code, message, status=503, retryable=False, field_errors=None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
        self.retryable, self.field_errors = retryable, field_errors or {}

    def as_dict(self):
        return {'code': self.code, 'message': self.message, 'retryable': self.retryable,
                'field_errors': self.field_errors}
