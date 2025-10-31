"""System health monitoring."""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from loguru import logger


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check configuration."""
    name: str
    check_func: Callable[[], Any]
    timeout_seconds: float = 5.0
    critical: bool = False  # If True, failure makes entire system unhealthy
    

@dataclass 
class HealthResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_seconds: float
    timestamp: float
    

class HealthChecker:
    """System health monitoring and checking."""
    
    def __init__(self) -> None:
        self.checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthResult] = {}
        self._monitoring = False
        
    def register_check(
        self,
        name: str,
        check_func: Callable[[], Any],
        timeout_seconds: float = 5.0,
        critical: bool = False
    ) -> None:
        """Register a health check."""
        self.checks[name] = HealthCheck(
            name=name,
            check_func=check_func,
            timeout_seconds=timeout_seconds,
            critical=critical
        )
        logger.info(f"Registered health check: {name}")
        
    async def run_check(self, name: str) -> HealthResult:
        """Run a single health check."""
        check = self.checks.get(name)
        if not check:
            return HealthResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found",
                duration_seconds=0.0,
                timestamp=time.time()
            )
            
        start_time = time.time()
        
        try:
            # Run check with timeout
            if asyncio.iscoroutinefunction(check.check_func):
                result = await asyncio.wait_for(
                    check.check_func(), 
                    timeout=check.timeout_seconds
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, check.check_func),
                    timeout=check.timeout_seconds
                )
                
            duration = time.time() - start_time
            
            # Interpret result
            if result is True or result == "OK":
                status = HealthStatus.HEALTHY
                message = "Check passed"
            elif isinstance(result, str):
                status = HealthStatus.HEALTHY if "OK" in result else HealthStatus.DEGRADED
                message = result
            else:
                status = HealthStatus.DEGRADED
                message = f"Check returned: {result}"
                
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"Check timed out after {check.timeout_seconds}s"
            
        except Exception as e:
            duration = time.time() - start_time
            status = HealthStatus.UNHEALTHY
            message = f"Check failed: {str(e)}"
            
        result = HealthResult(
            name=name,
            status=status,
            message=message,
            duration_seconds=duration,
            timestamp=time.time()
        )
        
        self.last_results[name] = result
        return result
        
    async def run_all_checks(self) -> Dict[str, HealthResult]:
        """Run all registered health checks."""
        if not self.checks:
            logger.warning("No health checks registered")
            return {}
            
        # Run all checks concurrently
        tasks = [
            self.run_check(name) for name in self.checks.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        check_results = {}
        for result in results:
            if isinstance(result, HealthResult):
                check_results[result.name] = result
            elif isinstance(result, Exception):
                logger.error(f"Health check failed with exception: {result}")
                
        return check_results
        
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.last_results:
            return HealthStatus.UNKNOWN
            
        has_critical_failure = False
        has_any_failure = False
        
        for name, result in self.last_results.items():
            check = self.checks.get(name)
            if not check:
                continue
                
            if result.status == HealthStatus.UNHEALTHY:
                has_any_failure = True
                if check.critical:
                    has_critical_failure = True
            elif result.status == HealthStatus.DEGRADED:
                has_any_failure = True
                
        if has_critical_failure:
            return HealthStatus.UNHEALTHY
        elif has_any_failure:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
            
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        overall_status = self.get_overall_status()
        
        checks_summary = {}
        for name, result in self.last_results.items():
            checks_summary[name] = {
                "status": result.status,
                "message": result.message,
                "duration_seconds": round(result.duration_seconds, 3),
                "last_check": result.timestamp
            }
            
        return {
            "overall_status": overall_status,
            "checks": checks_summary,
            "total_checks": len(self.checks),
            "last_updated": time.time()
        }
        
    async def start_monitoring(self, interval_seconds: float = 30.0) -> None:
        """Start continuous health monitoring."""
        self._monitoring = True
        logger.info(f"Starting health monitoring every {interval_seconds}s")
        
        while self._monitoring:
            try:
                await self.run_all_checks()
                status = self.get_overall_status()
                logger.debug(f"Health check completed: {status}")
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                
            await asyncio.sleep(interval_seconds)
            
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._monitoring = False
        logger.info("Health monitoring stopped")
        
    # Built-in health checks
    @staticmethod
    async def check_database_connection(db_url: str) -> str:
        """Check database connectivity."""
        try:
            # This would use your actual database connection
            # For now, just a placeholder
            await asyncio.sleep(0.1)  # Simulate DB check
            return "Database connection OK"
        except Exception as e:
            raise Exception(f"Database connection failed: {e}")
            
    @staticmethod
    async def check_redis_connection(redis_url: str) -> str:
        """Check Redis connectivity."""
        try:
            # This would use your actual Redis connection
            await asyncio.sleep(0.1)  # Simulate Redis check
            return "Redis connection OK"
        except Exception as e:
            raise Exception(f"Redis connection failed: {e}")
            
    @staticmethod
    def check_memory_usage(max_usage_percent: float = 80.0) -> str:
        """Check system memory usage."""
        import psutil
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        if usage_percent > max_usage_percent:
            raise Exception(f"High memory usage: {usage_percent}%")
            
        return f"Memory usage OK: {usage_percent}%"
        
    @staticmethod
    def check_disk_space(path: str = "/", max_usage_percent: float = 90.0) -> str:
        """Check disk space usage."""
        import psutil
        disk = psutil.disk_usage(path)
        usage_percent = (disk.used / disk.total) * 100
        
        if usage_percent > max_usage_percent:
            raise Exception(f"High disk usage: {usage_percent}%")
            
        return f"Disk usage OK: {usage_percent}%"