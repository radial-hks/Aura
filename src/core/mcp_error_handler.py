"""Enhanced error handling and recovery mechanisms for MCP connections.

This module provides comprehensive error handling, recovery mechanisms, and resilience patterns
for MCP (Model Context Protocol) connections. It implements industry-standard patterns like
circuit breakers, exponential backoff, connection pooling, and detailed error classification
to ensure robust and reliable MCP server interactions.

Core Components:
    - ErrorMetrics: Tracks error statistics and success rates
    - CircuitBreaker: Prevents cascading failures with automatic recovery
    - ExponentialBackoff: Implements intelligent retry strategies with jitter
    - ConnectionPool: Manages multiple MCP connections with health monitoring
    - MCPErrorHandler: Orchestrates error handling with fallback mechanisms

Key Features:
    - Automatic error classification and categorization
    - Circuit breaker pattern for fault tolerance
    - Exponential backoff with jitter for retry logic
    - Connection health monitoring and metrics
    - Graceful degradation with fallback operations
    - Comprehensive error reporting and diagnostics

Usage Example:
    ```python
    # Initialize error handling system
    pool = ConnectionPool(max_connections=10)
    handler = MCPErrorHandler(pool)
    
    # Add connections to pool
    pool.add_connection("server1", connection1)
    pool.add_connection("server2", connection2)
    
    # Execute operations with error handling
    result = await handler.execute_with_error_handling(
        "server1",
        lambda: server1.execute_command("test"),
        fallback=lambda: server2.execute_command("test")
    )
    ```

Architectural Considerations:
    - Designed for high-availability MCP deployments
    - Supports both synchronous and asynchronous operations
    - Provides detailed metrics for monitoring and alerting
    - Implements graceful degradation strategies
    - Optimized for minimal performance overhead
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import random
import json


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"


class ErrorType(Enum):
    """错误类型枚举"""
    CONNECTION_TIMEOUT = "connection_timeout"
    NETWORK_ERROR = "network_error"
    PROTOCOL_ERROR = "protocol_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorMetrics:
    """错误统计指标"""
    total_errors: int = 0
    error_rate: float = 0.0
    last_error_time: Optional[float] = None
    error_types: Dict[ErrorType, int] = field(default_factory=lambda: defaultdict(int))
    consecutive_failures: int = 0
    success_count: int = 0
    
    def record_error(self, error_type: ErrorType) -> None:
        """记录错误"""
        self.total_errors += 1
        self.error_types[error_type] += 1
        self.consecutive_failures += 1
        self.last_error_time = time.time()
        
    def record_success(self) -> None:
        """记录成功"""
        self.success_count += 1
        self.consecutive_failures = 0
        
    def calculate_error_rate(self, window_seconds: int = 300) -> float:
        """计算错误率"""
        total_operations = self.total_errors + self.success_count
        if total_operations == 0:
            return 0.0
        return self.total_errors / total_operations


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""
    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: int = 60  # 恢复超时（秒）
    half_open_max_calls: int = 3  # 半开状态最大调用次数
    

class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance.
    
    The circuit breaker prevents cascading failures by monitoring operation success/failure
    rates and automatically opening the circuit when failure thresholds are exceeded.
    It provides three states: CLOSED (normal), OPEN (failing), and HALF_OPEN (testing recovery).
    
    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Circuit is open, requests are rejected immediately
        - HALF_OPEN: Testing recovery, limited requests allowed
    
    Args:
        config (CircuitBreakerConfig): Configuration for failure thresholds and recovery
    
    Attributes:
        config: Circuit breaker configuration
        state: Current circuit state
        failure_count: Number of consecutive failures
        last_failure_time: Timestamp of last failure
        half_open_calls: Number of calls made in half-open state
    
    Example:
        ```python
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
        breaker = CircuitBreaker(config)
        
        if breaker.can_execute():
            try:
                result = await operation()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
        ```
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker with configuration.
        
        Args:
            config (CircuitBreakerConfig): Circuit breaker configuration parameters
        """
        self.config = config
        self.state = ConnectionState.CONNECTED  # Start in closed state
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
        
    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state.
        
        Determines whether requests should be allowed through based on the current
        circuit state and recovery logic. Automatically transitions from OPEN to
        HALF_OPEN state when recovery timeout has elapsed.
        
        Returns:
            bool: True if operation can proceed, False if circuit is open
            
        State Transitions:
            - CONNECTED: Always allows execution
            - CIRCUIT_OPEN: Allows execution only after recovery timeout
            - RECONNECTING (half-open): Allows limited executions for testing
        """
        if self.state == ConnectionState.CONNECTED:
            return True
        elif self.state == ConnectionState.CIRCUIT_OPEN:
            # 检查是否可以进入半开状态
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = ConnectionState.RECONNECTING  # 半开状态
                self.half_open_calls = 0
                self.logger.info("Circuit breaker entering half-open state")
                return True
            return False
        elif self.state == ConnectionState.RECONNECTING:
            return self.half_open_calls < self.config.half_open_max_calls
        return False
        
    def record_success(self) -> None:
        """记录成功操作"""
        if self.state == ConnectionState.RECONNECTING:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = ConnectionState.CONNECTED
                self.failure_count = 0
                self.logger.info("Circuit breaker closed - connection recovered")
        elif self.state == ConnectionState.CONNECTED:
            self.failure_count = 0
            
    def record_failure(self) -> None:
        """记录失败操作"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = ConnectionState.CIRCUIT_OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        elif self.state == ConnectionState.RECONNECTING:
            self.state = ConnectionState.CIRCUIT_OPEN
            self.logger.warning("Circuit breaker opened during half-open state")


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    

class ExponentialBackoff:
    """Exponential backoff retry mechanism with jitter.
    
    Implements intelligent retry logic with exponential backoff and optional jitter
    to prevent thundering herd problems. Supports configurable retry attempts,
    delay bounds, and error classification for retry decisions.
    
    Features:
        - Exponential delay calculation with configurable base and multiplier
        - Random jitter to prevent synchronized retries
        - Maximum delay cap to prevent excessive wait times
        - Error classification for retry eligibility
        - Comprehensive retry statistics and logging
    
    Args:
        config (RetryConfig): Retry configuration parameters
    
    Example:
        ```python
        config = RetryConfig(max_attempts=5, base_delay=1.0, max_delay=60.0)
        backoff = ExponentialBackoff(config)
        
        result = await backoff.execute_with_retry(
            lambda: risky_operation(),
            error_classifier=classify_error
        )
        ```
    """
    
    def __init__(self, config: RetryConfig):
        """Initialize exponential backoff with retry configuration.
        
        Args:
            config (RetryConfig): Configuration for retry behavior
        """
        self.config = config
        
    def calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if attempt <= 0:
            return 0
            
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** (attempt - 1)),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # 添加随机抖动，避免雷群效应
            jitter = delay * 0.1 * random.random()
            delay += jitter
            
        return delay
        
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        error_classifier: Optional[Callable[[Exception], ErrorType]] = None
    ) -> Any:
        """执行带重试的操作"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                error_type = error_classifier(e) if error_classifier else ErrorType.UNKNOWN_ERROR
                
                # 某些错误类型不应重试
                if error_type in [ErrorType.AUTHENTICATION_ERROR]:
                    raise e
                    
                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logging.getLogger(__name__).warning(
                        f"Operation failed (attempt {attempt}/{self.config.max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    
        raise last_exception


class ConnectionPool:
    """Connection pool manager for MCP server connections.
    
    Manages a pool of MCP connections with health monitoring, error tracking,
    and circuit breaker integration. Provides centralized connection lifecycle
    management and comprehensive health metrics.
    
    Features:
        - Dynamic connection addition and removal
        - Per-connection health monitoring and metrics
        - Integrated circuit breaker for each connection
        - Connection health assessment and filtering
        - Detailed statistics and error reporting
    
    Args:
        max_connections (int): Maximum number of connections in the pool
    
    Attributes:
        max_connections: Maximum allowed connections
        active_connections: Dictionary of active connection objects
        connection_metrics: Per-connection error and success metrics
        circuit_breakers: Per-connection circuit breaker instances
    
    Example:
        ```python
        pool = ConnectionPool(max_connections=10)
        pool.add_connection("server1", connection1)
        
        # Get healthy connections only
        healthy = pool.get_healthy_connections()
        
        # Record operation results
        pool.record_operation_result("server1", success=True)
        ```
    """
    
    def __init__(self, max_connections: int = 10):
        """Initialize connection pool with maximum connection limit.
        
        Args:
            max_connections (int): Maximum number of connections allowed in pool
        """
        self.max_connections = max_connections
        self.active_connections: Dict[str, Any] = {}  # Connection name -> connection object
        self.connection_metrics: Dict[str, ErrorMetrics] = {}  # Per-connection metrics
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}  # Per-connection circuit breakers
        self.logger = logging.getLogger(f"{__name__}.ConnectionPool")
        
    def add_connection(self, name: str, connection: Any) -> None:
        """添加连接到池中"""
        if len(self.active_connections) >= self.max_connections:
            raise RuntimeError(f"Connection pool full (max: {self.max_connections})")
            
        self.active_connections[name] = connection
        self.connection_metrics[name] = ErrorMetrics()
        self.circuit_breakers[name] = CircuitBreaker(CircuitBreakerConfig())
        self.logger.info(f"Added connection to pool: {name}")
        
    def remove_connection(self, name: str) -> None:
        """从池中移除连接"""
        if name in self.active_connections:
            del self.active_connections[name]
            del self.connection_metrics[name]
            del self.circuit_breakers[name]
            self.logger.info(f"Removed connection from pool: {name}")
            
    def get_connection(self, name: str) -> Optional[Any]:
        """获取连接"""
        return self.active_connections.get(name)
        
    def get_healthy_connections(self) -> Dict[str, Any]:
        """获取健康的连接"""
        healthy = {}
        for name, connection in self.active_connections.items():
            circuit_breaker = self.circuit_breakers[name]
            if circuit_breaker.can_execute():
                healthy[name] = connection
        return healthy
        
    def record_operation_result(self, name: str, success: bool, error_type: Optional[ErrorType] = None) -> None:
        """记录操作结果"""
        if name not in self.connection_metrics:
            return
            
        metrics = self.connection_metrics[name]
        circuit_breaker = self.circuit_breakers[name]
        
        if success:
            metrics.record_success()
            circuit_breaker.record_success()
        else:
            if error_type:
                metrics.record_error(error_type)
            circuit_breaker.record_failure()
            
    def get_connection_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取连接统计信息"""
        stats = {}
        for name in self.active_connections:
            metrics = self.connection_metrics[name]
            circuit_breaker = self.circuit_breakers[name]
            
            stats[name] = {
                "state": circuit_breaker.state.value,
                "total_errors": metrics.total_errors,
                "success_count": metrics.success_count,
                "consecutive_failures": metrics.consecutive_failures,
                "error_rate": metrics.calculate_error_rate(),
                "last_error_time": metrics.last_error_time,
                "error_types": {et.value: count for et, count in metrics.error_types.items()}
            }
            
        return stats


class MCPErrorHandler:
    """Comprehensive MCP error handler with retry and fallback mechanisms.
    
    Orchestrates error handling for MCP operations by combining circuit breakers,
    exponential backoff retries, error classification, and fallback strategies.
    Provides a unified interface for robust MCP operation execution.
    
    Core Responsibilities:
        - Execute operations with automatic retry logic
        - Classify errors for appropriate handling strategies
        - Manage circuit breaker states and health checks
        - Implement fallback mechanisms for degraded operations
        - Provide comprehensive error reporting and metrics
    
    Features:
        - Intelligent error classification and categorization
        - Automatic retry with exponential backoff
        - Circuit breaker integration for fault tolerance
        - Fallback operation support for graceful degradation
        - Detailed error statistics and health metrics
    
    Args:
        connection_pool (ConnectionPool): Pool of MCP connections to manage
    
    Example:
        ```python
        pool = ConnectionPool()
        handler = MCPErrorHandler(pool)
        
        # Execute with error handling and fallback
        result = await handler.execute_with_error_handling(
            "primary_server",
            lambda: primary_operation(),
            fallback=lambda: backup_operation()
        )
        
        # Get comprehensive error summary
        summary = handler.get_error_summary()
        ```
    
    Error Handling Flow:
        1. Check circuit breaker state for connection
        2. Execute operation with exponential backoff retry
        3. Classify any errors that occur
        4. Update connection metrics and circuit breaker
        5. Attempt fallback operation if primary fails
        6. Log comprehensive error information
    """
    
    def __init__(self, connection_pool: ConnectionPool):
        """Initialize error handler with connection pool.
        
        Args:
            connection_pool (ConnectionPool): Pool of connections to manage
        """
        self.connection_pool = connection_pool
        self.retry_handler = ExponentialBackoff(RetryConfig())  # Default retry configuration
        self.logger = logging.getLogger(__name__)
        
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error into predefined error types for appropriate handling.
        
        Analyzes exception messages and types to categorize errors into specific
        types that can be handled with different strategies. This classification
        drives retry decisions and error reporting.
        
        Args:
            error (Exception): The exception to classify
            
        Returns:
            ErrorType: Classified error type for handling strategy
            
        Error Classifications:
            - CONNECTION_TIMEOUT: Network timeouts and connection delays
            - NETWORK_ERROR: General network connectivity issues
            - AUTHENTICATION_ERROR: Authentication and authorization failures
            - PROTOCOL_ERROR: MCP protocol violations and invalid requests
            - RESOURCE_EXHAUSTED: Resource limits and capacity issues
            - UNKNOWN_ERROR: Unclassified or unexpected errors
            
        Note:
            Authentication errors are typically not retried as they indicate
            configuration issues rather than transient failures.
        """
        error_str = str(error).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.CONNECTION_TIMEOUT
        elif "connection" in error_str or "network" in error_str:
            return ErrorType.NETWORK_ERROR
        elif "auth" in error_str or "permission" in error_str:
            return ErrorType.AUTHENTICATION_ERROR
        elif "protocol" in error_str or "invalid" in error_str:
            return ErrorType.PROTOCOL_ERROR
        elif "resource" in error_str or "limit" in error_str:
            return ErrorType.RESOURCE_EXHAUSTED
        else:
            return ErrorType.UNKNOWN_ERROR
            
    async def execute_with_error_handling(
        self,
        connection_name: str,
        operation: Callable[[], Awaitable[Any]],
        fallback: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> Any:
        """Execute operation with comprehensive error handling and recovery.
        
        Orchestrates the complete error handling flow including circuit breaker
        checks, retry logic, error classification, metrics recording, and fallback
        execution. Provides robust operation execution with multiple recovery layers.
        
        Args:
            connection_name (str): Name of the connection to use for operation
            operation (Callable): Async operation to execute with error handling
            fallback (Optional[Callable]): Optional fallback operation if primary fails
            
        Returns:
            Any: Result of successful operation (primary or fallback)
            
        Raises:
            RuntimeError: If connection is unavailable and no fallback provided
            Exception: Original exception if both primary and fallback operations fail
            
        Execution Flow:
            1. Check circuit breaker state for connection availability
            2. Execute operation with exponential backoff retry logic
            3. Record success metrics and update circuit breaker on success
            4. On failure: classify error, record metrics, attempt fallback
            5. Log comprehensive error information for debugging
            
        Performance Considerations:
            - Circuit breaker prevents unnecessary retry attempts
            - Exponential backoff reduces system load during failures
            - Fallback operations provide graceful degradation
            - Metrics collection has minimal performance impact
        """
        circuit_breaker = self.connection_pool.circuit_breakers.get(connection_name)
        
        if not circuit_breaker or not circuit_breaker.can_execute():
            if fallback:
                self.logger.warning(f"Connection {connection_name} unavailable, using fallback")
                return await fallback()
            else:
                raise RuntimeError(f"Connection {connection_name} is not available")
                
        try:
            result = await self.retry_handler.execute_with_retry(
                operation,
                error_classifier=self.classify_error
            )
            
            # 记录成功
            self.connection_pool.record_operation_result(connection_name, True)
            return result
            
        except Exception as e:
            error_type = self.classify_error(e)
            
            # 记录失败
            self.connection_pool.record_operation_result(connection_name, False, error_type)
            
            self.logger.error(f"Operation failed on {connection_name}: {e} (type: {error_type.value})")
            
            # 尝试降级处理
            if fallback:
                self.logger.info(f"Attempting fallback for {connection_name}")
                try:
                    return await fallback()
                except Exception as fallback_error:
                    self.logger.error(f"Fallback also failed: {fallback_error}")
                    
            raise e
            
    def get_error_summary(self) -> Dict[str, Any]:
        """Generate comprehensive error summary and health metrics.
        
        Aggregates error statistics, connection health, and system-wide metrics
        to provide a complete view of MCP error handling performance and system health.
        
        Returns:
            Dict[str, Any]: Comprehensive error summary containing:
                - total_connections: Total number of managed connections
                - healthy_connections: Number of currently healthy connections
                - connections: Per-connection detailed statistics
                - overall_error_rate: System-wide error rate calculation
                - most_common_errors: Aggregated error type frequencies
                
        Summary Structure:
            ```python
            {
                "total_connections": 5,
                "healthy_connections": 4,
                "overall_error_rate": 0.05,
                "connections": {
                    "server1": {
                        "state": "connected",
                        "total_errors": 2,
                        "success_count": 98,
                        "error_rate": 0.02,
                        "error_types": {"network_error": 2}
                    }
                },
                "most_common_errors": {
                    "network_error": 5,
                    "timeout_error": 3
                }
            }
            ```
            
        Usage Scenarios:
            - System health monitoring and alerting
            - Performance analysis and optimization
            - Debugging connection issues
            - Capacity planning and scaling decisions
            - Error trend analysis and reporting
        """
        stats = self.connection_pool.get_connection_stats()
        
        summary = {
            "total_connections": len(stats),
            "healthy_connections": len(self.connection_pool.get_healthy_connections()),
            "connections": stats,
            "overall_error_rate": 0.0,
            "most_common_errors": defaultdict(int)
        }
        
        # 计算整体错误率和最常见错误
        total_operations = 0
        total_errors = 0
        
        for conn_stats in stats.values():
            total_operations += conn_stats["total_errors"] + conn_stats["success_count"]
            total_errors += conn_stats["total_errors"]
            
            for error_type, count in conn_stats["error_types"].items():
                summary["most_common_errors"][error_type] += count
                
        if total_operations > 0:
            summary["overall_error_rate"] = total_errors / total_operations
            
        # 转换为普通字典
        summary["most_common_errors"] = dict(summary["most_common_errors"])
        
        return summary