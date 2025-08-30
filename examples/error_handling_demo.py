#!/usr/bin/env python3
"""
MCP Error Handling and Reconnection Demo

This script demonstrates the enhanced error handling and auto-reconnection
capabilities of the MCP Manager system.
"""

import asyncio
import logging
import time
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.mcp_manager import MCPManager
from core.mcp_error_handler import ConnectionState, ErrorType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlingDemo:
    """Demonstration of MCP error handling capabilities"""
    
    def __init__(self):
        self.manager = MCPManager()
        self.demo_servers = [
            ("playwright_demo", "playwright", {"host": "localhost", "port": 3001}),
            ("filesystem_demo", "filesystem", {"path": "/tmp"}),
            ("search_demo", "search", {"api_key": "demo_key"}),
            ("memory_demo", "memory", {"storage_path": "./demo_memory"})
        ]
    
    async def setup_demo_environment(self):
        """Set up the demo environment with test servers"""
        logger.info("Setting up demo environment...")
        
        # Add demo servers
        for server_name, server_type, config in self.demo_servers:
            self.manager.add_server(server_name, server_type, config)
            logger.info(f"Added server: {server_name} ({server_type})")
        
        # Initialize the manager (this will attempt connections)
        try:
            await self.manager.initialize()
            logger.info("MCP Manager initialized successfully")
        except Exception as e:
            logger.warning(f"Initial connection failed (expected): {e}")
            logger.info("This is normal for demo - servers may not be running")
    
    async def demonstrate_connection_states(self):
        """Demonstrate connection state tracking"""
        logger.info("\n=== Connection State Demonstration ===")
        
        states = self.manager.get_connection_states()
        for server_name, state in states.items():
            logger.info(f"Server {server_name}: {state.value}")
        
        # Show connection state transitions
        logger.info("\nSimulating connection state changes...")
        for server_name in states.keys():
            # Simulate connection attempt
            self.manager._connection_states[server_name] = ConnectionState.CONNECTING
            logger.info(f"{server_name}: DISCONNECTED -> CONNECTING")
            
            await asyncio.sleep(0.5)
            
            # Simulate connection failure
            self.manager._connection_states[server_name] = ConnectionState.RECONNECTING
            logger.info(f"{server_name}: CONNECTING -> RECONNECTING")
            
            await asyncio.sleep(0.5)
    
    async def demonstrate_error_classification(self):
        """Demonstrate error type classification"""
        logger.info("\n=== Error Classification Demonstration ===")
        
        test_errors = [
            (ConnectionError("Connection refused"), "Network Error"),
            (TimeoutError("Operation timed out"), "Timeout Error"),
            (PermissionError("Access denied"), "Authentication Error"),
            (ValueError("Invalid parameter"), "Unknown Error")
        ]
        
        for error, description in test_errors:
            error_type = self.manager._error_handler.classify_error(error)
            logger.info(f"{description}: {error_type.value}")
            
            # Record the error for statistics
            self.manager._error_handler.error_metrics.record_error(
                "demo_server", error_type
            )
    
    async def demonstrate_circuit_breaker(self):
        """Demonstrate circuit breaker functionality"""
        logger.info("\n=== Circuit Breaker Demonstration ===")
        
        server_name = "demo_circuit_breaker"
        circuit_breaker = self.manager._error_handler.circuit_breaker
        
        logger.info(f"Initial state - Circuit breaker closed: {not circuit_breaker.is_open(server_name)}")
        
        # Simulate failures to trigger circuit breaker
        logger.info("Simulating failures...")
        for i in range(4):
            circuit_breaker.record_failure(server_name)
            is_open = circuit_breaker.is_open(server_name)
            logger.info(f"Failure {i+1}: Circuit breaker open = {is_open}")
            
            if is_open:
                logger.info("Circuit breaker opened - preventing further attempts")
                break
        
        # Simulate recovery timeout
        logger.info("Waiting for recovery timeout...")
        await asyncio.sleep(2)
        
        can_attempt = circuit_breaker.can_attempt(server_name)
        logger.info(f"After timeout - Can attempt reconnection: {can_attempt}")
        
        if can_attempt:
            # Simulate successful recovery
            circuit_breaker.record_success(server_name)
            logger.info("Successful operation recorded - circuit breaker reset")
    
    async def demonstrate_health_monitoring(self):
        """Demonstrate health monitoring and metrics"""
        logger.info("\n=== Health Monitoring Demonstration ===")
        
        # Simulate some health check data
        for server_name, _, _ in self.demo_servers:
            # Simulate different health states
            if "playwright" in server_name:
                self.manager._connection_states[server_name] = ConnectionState.CONNECTED
                self.manager._health_check_failures[server_name] = 0
            elif "filesystem" in server_name:
                self.manager._connection_states[server_name] = ConnectionState.RECONNECTING
                self.manager._health_check_failures[server_name] = 2
            else:
                self.manager._connection_states[server_name] = ConnectionState.DISCONNECTED
                self.manager._health_check_failures[server_name] = 5
        
        # Update last health check time
        self.manager._last_health_check = time.time()
        
        # Get and display health metrics
        metrics = self.manager.get_health_metrics()
        logger.info("Health Metrics:")
        for key, value in metrics.items():
            if key == "last_health_check":
                logger.info(f"  {key}: {time.ctime(value)}")
            else:
                logger.info(f"  {key}: {value}")
    
    async def demonstrate_error_statistics(self):
        """Demonstrate error statistics collection"""
        logger.info("\n=== Error Statistics Demonstration ===")
        
        # Simulate various errors for different servers
        error_scenarios = [
            ("playwright_demo", ErrorType.NETWORK, 3),
            ("playwright_demo", ErrorType.TIMEOUT, 1),
            ("filesystem_demo", ErrorType.AUTHENTICATION, 2),
            ("search_demo", ErrorType.RATE_LIMIT, 5),
            ("memory_demo", ErrorType.UNKNOWN, 1)
        ]
        
        for server_name, error_type, count in error_scenarios:
            for _ in range(count):
                self.manager._error_handler.error_metrics.record_error(server_name, error_type)
        
        # Get and display error statistics
        stats = self.manager.get_error_statistics()
        logger.info("Error Statistics:")
        for server_name, server_stats in stats.items():
            logger.info(f"  {server_name}:")
            logger.info(f"    Total errors: {server_stats['total_errors']}")
            logger.info(f"    Error rate: {server_stats['error_rate']:.2f} errors/min")
            logger.info(f"    Error types:")
            for error_type, count in server_stats['error_types'].items():
                logger.info(f"      {error_type}: {count}")
    
    async def demonstrate_connection_diagnostics(self):
        """Demonstrate connection diagnostics"""
        logger.info("\n=== Connection Diagnostics Demonstration ===")
        
        # Run diagnostics
        diagnostics = self.manager.diagnose_connection_issues()
        
        logger.info("Connection Diagnostics:")
        for server_name, diagnosis in diagnostics.items():
            logger.info(f"  {server_name}:")
            logger.info(f"    Status: {diagnosis['status']}")
            logger.info(f"    Connection state: {diagnosis['connection_state']}")
            logger.info(f"    Failure count: {diagnosis['failure_count']}")
            logger.info(f"    Last error: {diagnosis['last_error']}")
            
            if diagnosis['issues']:
                logger.info(f"    Issues: {', '.join(diagnosis['issues'])}")
            
            if diagnosis['recommendations']:
                logger.info(f"    Recommendations: {', '.join(diagnosis['recommendations'])}")
    
    async def demonstrate_recovery_scenarios(self):
        """Demonstrate various recovery scenarios"""
        logger.info("\n=== Recovery Scenarios Demonstration ===")
        
        # Scenario 1: Single server reconnection
        logger.info("Scenario 1: Single server reconnection")
        server_name = "playwright_demo"
        self.manager._connection_states[server_name] = ConnectionState.DISCONNECTED
        self.manager._health_check_failures[server_name] = 3
        
        logger.info(f"Before: {server_name} is {self.manager._connection_states[server_name].value}")
        
        # Simulate successful reconnection
        await self.manager._attempt_reconnect_single_server(server_name)
        
        logger.info(f"After: {server_name} is {self.manager._connection_states[server_name].value}")
        
        # Scenario 2: Multiple server failures
        logger.info("\nScenario 2: Multiple server failures")
        failed_servers = ["filesystem_demo", "search_demo"]
        
        for server in failed_servers:
            self.manager._connection_states[server] = ConnectionState.DISCONNECTED
            self.manager._health_check_failures[server] = 5
            logger.info(f"{server} marked as failed")
        
        # Simulate health check and recovery attempts
        logger.info("Running health check and recovery...")
        await self.manager._perform_health_check()
        
        for server in failed_servers:
            state = self.manager._connection_states[server]
            logger.info(f"{server} state after recovery attempt: {state.value}")
    
    async def run_complete_demo(self):
        """Run the complete error handling demonstration"""
        logger.info("Starting MCP Error Handling and Reconnection Demo")
        logger.info("=" * 60)
        
        try:
            await self.setup_demo_environment()
            await self.demonstrate_connection_states()
            await self.demonstrate_error_classification()
            await self.demonstrate_circuit_breaker()
            await self.demonstrate_health_monitoring()
            await self.demonstrate_error_statistics()
            await self.demonstrate_connection_diagnostics()
            await self.demonstrate_recovery_scenarios()
            
            logger.info("\n=== Demo Summary ===")
            logger.info("Demonstrated features:")
            logger.info("✓ Connection state tracking")
            logger.info("✓ Error classification and statistics")
            logger.info("✓ Circuit breaker pattern")
            logger.info("✓ Health monitoring and metrics")
            logger.info("✓ Connection diagnostics")
            logger.info("✓ Automatic recovery scenarios")
            
        except Exception as e:
            logger.error(f"Demo failed with error: {e}")
            raise
        finally:
            # Cleanup
            await self.manager.shutdown()
            logger.info("Demo completed and resources cleaned up")


async def main():
    """Main demo function"""
    demo = ErrorHandlingDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())