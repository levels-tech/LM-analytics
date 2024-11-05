##FILE DI ECCEZIONI 

"""
Custom exceptions for the application.
Contains all custom exception classes with descriptive error messages.
"""

class SkipMatcherException(Exception):
    """skippare classe se non ci sono pagamenti"""
    pass


class BaseError(Exception):
    """Base exception class for the application."""
    def __init__(self, message="Si è verificato un errore", details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)

# File Processing Errors
class FileProcessingError(BaseError):
    """Base class for file processing errors."""
    def __init__(self, message="Errore durante l'elaborazione del file", details=None):
        super().__init__(message, details)

class FileValidationError(FileProcessingError):
    """Raised when file content validation fails."""
    def __init__(self, message="Errore nella validazione del file", details=None):
        super().__init__(message, details)


class DateMismatchError(FileValidationError):
    """Raised when dates in the file don't match the expected period."""
    def __init__(self, message="Le date nel file non corrispondono al periodo selezionato", details=None):
        super().__init__(message, details)

########################################################   



# # Order Processing Errors
# class OrderProcessingError(BaseError):
#     """Base class for order processing errors."""
#     def __init__(self, message="Errore durante l'elaborazione dell'ordine", details=None):
#         super().__init__(message, details)

# class InvalidAmountError(OrderProcessingError):
#     """Raised when an amount value is invalid."""
#     def __init__(self, message="Importo non valido", details=None):
#         super().__init__(message, details)

# class OrderNotFoundError(OrderProcessingError):
#     """Raised when an order cannot be found."""
#     def __init__(self, message="Ordine non trovato", details=None):
#         super().__init__(message, details)

# class PaymentMismatchError(OrderProcessingError):
#     """Raised when there's a discrepancy in payment amounts."""
#     def __init__(self, message="Differenza tra importo pagato e totale ordine", details=None):
#         super().__init__(message, details)


# class FileUploadError(FileProcessingError):
#     """Raised when there's an error uploading files."""
#     def __init__(self, message="Errore durante il caricamento del file", details=None):
#         super().__init__(message, details)

# class InvalidFileFormatError(FileProcessingError):
#     """Raised when file format is invalid."""
#     def __init__(self, message="Formato file non valido", details=None):
#         super().__init__(message, details)

# # Data Validation Errors
# class ValidationError(BaseError):
#     """Base class for validation errors."""
#     def __init__(self, message="Errore di validazione", details=None):
#         super().__init__(message, details)

# class QuantityError(ValidationError):
#     """Raised when there's an issue with order quantities."""
#     def __init__(self, message="Errore nelle quantità specificate", details=None):
#         super().__init__(message, details)

# class DataConsistencyError(ValidationError):
#     """Raised when there are data consistency issues."""
#     def __init__(self, message="Errore di consistenza dei dati", details=None):
#         super().__init__(message, details)

# # Payment Processing Errors
# class PaymentProcessingError(BaseError):
#     """Base class for payment processing errors."""
#     def __init__(self, message="Errore durante l'elaborazione del pagamento", details=None):
#         super().__init__(message, details)

# class PaymentNotFoundError(PaymentProcessingError):
#     """Raised when a payment cannot be found."""
#     def __init__(self, message="Pagamento non trovato", details=None):
#         super().__init__(message, details)

# class DuplicatePaymentError(PaymentProcessingError):
#     """Raised when a duplicate payment is detected."""
#     def __init__(self, message="Pagamento duplicato rilevato", details=None):
#         super().__init__(message, details)
