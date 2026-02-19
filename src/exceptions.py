"""
TrendSignal - Custom Exceptions for Trackback System
Trade management error handling

Version: 1.0
Date: 2026-02-17
"""


class TrackbackException(Exception):
    """Base exception for all trackback system errors"""
    pass


class PositionAlreadyExistsError(TrackbackException):
    """Raised when trying to open a position for a ticker that already has an open position"""
    def __init__(self, symbol: str, existing_trade_id: int = None):
        self.symbol = symbol
        self.existing_trade_id = existing_trade_id
        message = f"Open position already exists for {symbol}"
        if existing_trade_id:
            message += f" (trade_id: {existing_trade_id})"
        super().__init__(message)


class InsufficientDataError(TrackbackException):
    """Raised when required price data is not available"""
    def __init__(self, symbol: str, timestamp: str, interval: str = "5m"):
        self.symbol = symbol
        self.timestamp = timestamp
        self.interval = interval
        message = f"No {interval} price data available for {symbol} at {timestamp}"
        super().__init__(message)


class InvalidSignalError(TrackbackException):
    """Raised when signal data is invalid or incomplete"""
    def __init__(self, signal_id: int, reason: str):
        self.signal_id = signal_id
        self.reason = reason
        message = f"Invalid signal {signal_id}: {reason}"
        super().__init__(message)


class PositionNotFoundError(TrackbackException):
    """Raised when trying to close a position that doesn't exist"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        message = f"No open position found for {symbol}"
        super().__init__(message)


class ExchangeRateError(TrackbackException):
    """Raised when USD/HUF exchange rate cannot be fetched"""
    def __init__(self, reason: str = "Unable to fetch exchange rate"):
        self.reason = reason
        super().__init__(f"Exchange rate error: {reason}")
