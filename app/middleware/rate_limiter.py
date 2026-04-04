"""
Core Rate Limiter
Main rate limiting logic with multiple algorithms and fallback strategies
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .rate_limit_storage import RateLimitStorage, RateLimitResult, rate_limit_storage
from .rate_limit_config import RateLimitConfig, RateLimitRule, UserType, rate_limit_config

logger = logging.getLogger(__name__)


@dataclass
class RateLimitCheckResult:
    """Complete result of rate limit checking"""
    allowed: bool
    results: List[Tuple[str, RateLimitResult]]  # (rule_type, result)
    headers: Dict[str, str]
    user_type: UserType
    identifier: str
    endpoint: str
    
    @property
    def most_restrictive_result(self) -> Optional[RateLimitResult]:
        """Get the most restrictive (first failed) result"""
        for rule_type, result in self.results:
            if not result.allowed:
                return result
        return None
    
    @property
    def retry_after(self) -> Optional[int]:
        """Get retry after seconds from most restrictive result"""
        restrictive = self.most_restrictive_result
        return restrictive.retry_after if restrictive else None


class RateLimiter:
    """Main rate limiter class"""
    
    def __init__(self, 
                 storage: Optional[RateLimitStorage] = None,
                 config: Optional[RateLimitConfig] = None):
        self.storage = storage or rate_limit_storage
        self.config = config or rate_limit_config
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "errors": 0,
            "circuit_breaker_open": 0
        }
    
    async def check_rate_limit(self, request_info: Dict[str, Any]) -> RateLimitCheckResult:
        """
        Check rate limits for a request
        
        Args:
            request_info: Dictionary containing:
                - endpoint: str - API endpoint path
                - user_id: Optional[str] - User ID if authenticated
                - ip_address: str - Client IP address
                - permissions: List[str] - User permissions
                - is_premium: bool - Whether user is premium
        
        Returns:
            RateLimitCheckResult with all check results
        """
        self._stats["total_requests"] += 1
        
        # Check if rate limiting is enabled
        if not self.config.is_enabled():
            logger.debug("Rate limiting is disabled")
            return RateLimitCheckResult(
                allowed=True,
                results=[],
                headers={},
                user_type=UserType.ANONYMOUS,
                identifier="disabled",
                endpoint=request_info.get("endpoint", "unknown")
            )
        
        endpoint = request_info.get("endpoint", "")
        user_type = self.config.get_user_type_from_request(request_info)
        
        # Get applicable rules
        applicable_rules = self.config.get_applicable_rules(endpoint, user_type)
        
        if not applicable_rules:
            logger.debug(f"No rate limit rules found for endpoint: {endpoint}")
            return RateLimitCheckResult(
                allowed=True,
                results=[],
                headers={},
                user_type=user_type,
                identifier="no_rules",
                endpoint=endpoint
            )
        
        # Check each applicable rule
        results = []
        overall_allowed = True
        combined_headers = {}
        
        for rule_type, rule in applicable_rules:
            try:
                # Generate identifier for this rule
                identifier = self.config.get_identifier(request_info, rule_type)
                
                # Perform rate limit check
                if rule.algorithm.value == "sliding_window":
                    result = await self.storage.sliding_window_check(
                        identifier=identifier,
                        limit=rule.limit,
                        window_size=rule.window
                    )
                else:  # fixed_window
                    result = await self.storage.fixed_window_check(
                        identifier=identifier,
                        limit=rule.limit,
                        window_size=rule.window
                    )
                
                results.append((rule_type, result))
                
                # Generate headers for this rule
                rule_headers = self.config.get_rate_limit_headers(result, rule)
                
                # Use the most restrictive headers
                if rule_type == "endpoint" or not combined_headers:
                    combined_headers.update(rule_headers)
                
                # If any rule fails, overall request is not allowed
                if not result.allowed:
                    overall_allowed = False
                    logger.info(f"Rate limit exceeded for {rule_type} rule: {identifier}")
                    break  # Stop checking further rules
                
            except Exception as e:
                logger.error(f"Error checking {rule_type} rate limit: {e}")
                self._stats["errors"] += 1
                
                # On error, allow request (fail-open strategy)
                error_result = RateLimitResult(
                    allowed=True,
                    current_count=0,
                    limit=rule.limit,
                    window_size=rule.window,
                    reset_time=int(time.time() + rule.window)
                )
                results.append((rule_type, error_result))
        
        # Update statistics
        if overall_allowed:
            self._stats["allowed_requests"] += 1
        else:
            self._stats["blocked_requests"] += 1
        
        # Get primary identifier (from first rule)
        primary_identifier = "unknown"
        if applicable_rules:
            primary_identifier = self.config.get_identifier(
                request_info, 
                applicable_rules[0][0]
            )
        
        return RateLimitCheckResult(
            allowed=overall_allowed,
            results=results,
            headers=combined_headers,
            user_type=user_type,
            identifier=primary_identifier,
            endpoint=endpoint
        )
    
    async def get_rate_limit_status(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get current rate limit status for request"""
        endpoint = request_info.get("endpoint", "")
        user_type = self.config.get_user_type_from_request(request_info)
        applicable_rules = self.config.get_applicable_rules(endpoint, user_type)
        
        status = {
            "endpoint": endpoint,
            "user_type": user_type.value,
            "rate_limiting_enabled": self.config.is_enabled(),
            "rules": []
        }
        
        for rule_type, rule in applicable_rules:
            identifier = self.config.get_identifier(request_info, rule_type)
            
            try:
                info = await self.storage.get_rate_limit_info(identifier, rule.window)
                rule_status = {
                    "type": rule_type,
                    "identifier": identifier,
                    "limit": rule.limit,
                    "window": rule.window,
                    "algorithm": rule.algorithm.value,
                    "description": rule.description,
                    "current_info": info
                }
                status["rules"].append(rule_status)
                
            except Exception as e:
                logger.error(f"Error getting rate limit status: {e}")
                status["rules"].append({
                    "type": rule_type,
                    "identifier": identifier,
                    "error": str(e)
                })
        
        return status
    
    async def reset_rate_limit(self, request_info: Dict[str, Any]) -> Dict[str, bool]:
        """Reset rate limits for request"""
        endpoint = request_info.get("endpoint", "")
        user_type = self.config.get_user_type_from_request(request_info)
        applicable_rules = self.config.get_applicable_rules(endpoint, user_type)
        
        results = {}
        
        for rule_type, rule in applicable_rules:
            identifier = self.config.get_identifier(request_info, rule_type)
            
            try:
                success = await self.storage.reset_rate_limit(identifier)
                results[f"{rule_type}_{identifier}"] = success
                
            except Exception as e:
                logger.error(f"Error resetting rate limit: {e}")
                results[f"{rule_type}_{identifier}"] = False
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        total = self._stats["total_requests"]
        
        stats = self._stats.copy()
        stats.update({
            "success_rate": (self._stats["allowed_requests"] / total * 100) if total > 0 else 0,
            "block_rate": (self._stats["blocked_requests"] / total * 100) if total > 0 else 0,
            "error_rate": (self._stats["errors"] / total * 100) if total > 0 else 0,
            "circuit_breaker_state": self.storage.circuit_breaker.state,
            "storage_type": self.config.storage_type,
            "enabled": self.config.is_enabled()
        })
        
        return stats
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self._stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "errors": 0,
            "circuit_breaker_open": 0
        }
        logger.info("Rate limiter statistics reset")


# Global rate limiter instance
rate_limiter = RateLimiter()


# Convenience functions
async def check_rate_limit(request_info: Dict[str, Any]) -> RateLimitCheckResult:
    """Check rate limit for request"""
    return await rate_limiter.check_rate_limit(request_info)


async def get_rate_limit_status(request_info: Dict[str, Any]) -> Dict[str, Any]:
    """Get rate limit status for request"""
    return await rate_limiter.get_rate_limit_status(request_info)


async def reset_rate_limit(request_info: Dict[str, Any]) -> Dict[str, bool]:
    """Reset rate limit for request"""
    return await rate_limiter.reset_rate_limit(request_info)


def get_rate_limiter_stats() -> Dict[str, Any]:
    """Get rate limiter statistics"""
    return rate_limiter.get_statistics()