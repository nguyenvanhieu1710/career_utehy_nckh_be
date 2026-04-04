"""
Rate Limit Configuration and Rules
Defines rate limiting rules for different endpoints and user types
"""
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class UserType(Enum):
    """User types for different rate limits"""
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"
    PREMIUM = "premium"


@dataclass
class RateLimitRule:
    """Rate limit rule definition"""
    limit: int                              # Max requests allowed
    window: int                             # Time window in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    user_types: List[UserType] = None       # Applicable user types
    description: str = ""                   # Rule description
    
    def __post_init__(self):
        if self.user_types is None:
            self.user_types = [UserType.ANONYMOUS, UserType.AUTHENTICATED]


class RateLimitConfig:
    """Rate limiting configuration manager"""
    
    def __init__(self):
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
        self.storage_type = os.getenv("RATE_LIMIT_STORAGE", "redis")
        self.default_algorithm = RateLimitAlgorithm.SLIDING_WINDOW
        
        # Development mode settings
        self.dev_mode = os.getenv("DEV_MODE", "False").lower() == "true"
        self.dev_multiplier = int(os.getenv("RATE_LIMIT_DEV_MULTIPLIER", "1"))
        
        # Global settings
        self.fail_open = True  # Allow requests when rate limiting fails
        self.include_headers = True  # Include rate limit headers in response
        
        # Initialize endpoint rules
        self._endpoint_rules = self._load_endpoint_rules()
        self._global_rules = self._load_global_rules()
        
        # Apply dev mode multiplier if enabled
        if self.dev_mode:
            self._apply_dev_mode_multiplier()
    
    def _apply_dev_mode_multiplier(self):
        """Apply development mode multiplier to all rules"""
        if self.dev_multiplier <= 1:
            return
            
        logger.info(f"🚀 DEV MODE: Applying {self.dev_multiplier}x multiplier to all rate limits")
        
        # Apply to endpoint rules
        for endpoint, rule in self._endpoint_rules.items():
            original_limit = rule.limit
            rule.limit = rule.limit * self.dev_multiplier
            logger.debug(f"   {endpoint}: {original_limit} → {rule.limit}")
        
        # Apply to global rules
        for user_type, rule in self._global_rules.items():
            original_limit = rule.limit
            rule.limit = rule.limit * self.dev_multiplier
            logger.debug(f"   Global {user_type.value}: {original_limit} → {rule.limit}")
    
    def _load_endpoint_rules(self) -> Dict[str, RateLimitRule]:
        """Load endpoint-specific rate limiting rules"""
        return {
            # Authentication endpoints - Strict limits
            "/api/v1/auth/login": RateLimitRule(
                limit=5,
                window=60,  # 5 requests per minute
                description="Login attempts - prevent brute force"
            ),
            "/api/v1/auth/signup": RateLimitRule(
                limit=3,
                window=300,  # 3 requests per 5 minutes
                description="Signup attempts - prevent spam accounts"
            ),
            "/api/v1/auth/refresh-token": RateLimitRule(
                limit=10,
                window=60,  # 10 requests per minute
                description="Token refresh - moderate limit"
            ),
            "/api/v1/auth/change-password": RateLimitRule(
                limit=3,
                window=300,  # 3 requests per 5 minutes
                description="Password changes - security sensitive"
            ),
            
            # Chat/AI endpoints - Moderate limits
            "/api/v1/chat/stream": RateLimitRule(
                limit=10,
                window=60,  # 10 requests per minute
                user_types=[UserType.AUTHENTICATED],
                description="AI chat streaming - resource intensive"
            ),
            "/api/v1/chat/rebuild-index": RateLimitRule(
                limit=1,
                window=300,  # 1 request per 5 minutes
                user_types=[UserType.ADMIN],
                description="Index rebuild - admin only, very resource intensive"
            ),
            
            # Upload endpoints - Very strict limits
            "/api/v1/upload": RateLimitRule(
                limit=5,
                window=60,  # 5 uploads per minute
                user_types=[UserType.AUTHENTICATED],
                description="File uploads - bandwidth intensive"
            ),
            "/api/v1/auth/upload-avatar": RateLimitRule(
                limit=3,
                window=300,  # 3 avatar uploads per 5 minutes
                user_types=[UserType.AUTHENTICATED],
                description="Avatar uploads - prevent abuse"
            ),
            
            # Email endpoints - Strict limits
            "/api/v1/email": RateLimitRule(
                limit=5,
                window=300,  # 5 emails per 5 minutes
                description="Email sending - prevent spam"
            ),
            
            # Payment endpoints - Moderate limits
            "/api/v1/payment": RateLimitRule(
                limit=10,
                window=60,  # 10 payment requests per minute
                user_types=[UserType.AUTHENTICATED],
                description="Payment processing - financial security"
            ),
            
            # Public job endpoints - Higher limits
            "/api/v1/public": RateLimitRule(
                limit=100,
                window=60,  # 100 requests per minute
                description="Public job listings - high traffic allowed"
            ),
            "/api/v1/job": RateLimitRule(
                limit=50,
                window=60,  # 50 requests per minute
                user_types=[UserType.AUTHENTICATED],
                description="Job operations - moderate limit"
            ),
            "/api/v1/job-mongo": RateLimitRule(
                limit=30,
                window=60,  # 30 requests per minute
                user_types=[UserType.AUTHENTICATED],
                description="MongoDB job operations - database intensive"
            ),
            
            # Company endpoints
            "/api/v1/company": RateLimitRule(
                limit=50,
                window=60,  # 50 requests per minute
                description="Company information - moderate limit"
            ),
            
            # CV endpoints
            "/api/v1/cv": RateLimitRule(
                limit=20,
                window=60,  # 20 requests per minute
                user_types=[UserType.AUTHENTICATED],
                description="CV operations - moderate limit"
            ),
            
            # Category endpoints
            "/api/v1/category": RateLimitRule(
                limit=100,
                window=60,  # 100 requests per minute
                description="Category listings - high traffic allowed"
            ),
            
            # Admin endpoints - Higher limits for authenticated admins
            "/api/v1/permission": RateLimitRule(
                limit=50,
                window=60,  # 50 requests per minute
                user_types=[UserType.ADMIN],
                description="Permission management - admin operations"
            ),
            
            # Common/utility endpoints
            "/api/v1/common": RateLimitRule(
                limit=200,
                window=60,  # 200 requests per minute
                description="Common utilities - high limit"
            ),
        }
    
    def _load_global_rules(self) -> Dict[UserType, RateLimitRule]:
        """Load global rate limiting rules by user type"""
        return {
            UserType.ANONYMOUS: RateLimitRule(
                limit=100,
                window=60,  # 100 requests per minute for anonymous users
                description="Global limit for anonymous users"
            ),
            UserType.AUTHENTICATED: RateLimitRule(
                limit=500,
                window=60,  # 500 requests per minute for authenticated users
                description="Global limit for authenticated users"
            ),
            UserType.ADMIN: RateLimitRule(
                limit=1000,
                window=60,  # 1000 requests per minute for admins
                description="Global limit for admin users"
            ),
            UserType.PREMIUM: RateLimitRule(
                limit=2000,
                window=60,  # 2000 requests per minute for premium users
                description="Global limit for premium users"
            ),
        }
    
    def get_endpoint_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Get rate limit rule for specific endpoint"""
        # Direct match first
        if endpoint in self._endpoint_rules:
            return self._endpoint_rules[endpoint]
        
        # Pattern matching for dynamic routes
        for pattern, rule in self._endpoint_rules.items():
            if self._match_endpoint_pattern(pattern, endpoint):
                return rule
        
        return None
    
    def get_global_rule(self, user_type: UserType) -> RateLimitRule:
        """Get global rate limit rule for user type"""
        return self._global_rules.get(user_type, self._global_rules[UserType.ANONYMOUS])
    
    def _match_endpoint_pattern(self, pattern: str, endpoint: str) -> bool:
        """Match endpoint against pattern (supports wildcards)"""
        # Convert pattern to regex
        # Replace {id} with regex pattern for UUIDs or numbers
        regex_pattern = pattern
        regex_pattern = regex_pattern.replace("{id}", r"[a-fA-F0-9\-]+")
        regex_pattern = regex_pattern.replace("{user_id}", r"[a-fA-F0-9\-]+")
        regex_pattern = regex_pattern.replace("{target_user_id}", r"[a-fA-F0-9\-]+")
        regex_pattern = regex_pattern.replace("*", ".*")
        
        # Add anchors
        regex_pattern = f"^{regex_pattern}$"
        
        try:
            return bool(re.match(regex_pattern, endpoint))
        except re.error:
            return False
    
    def get_applicable_rules(self, endpoint: str, user_type: UserType) -> List[Tuple[str, RateLimitRule]]:
        """Get all applicable rate limit rules for endpoint and user type"""
        rules = []
        
        # Add endpoint-specific rule if exists and applicable
        endpoint_rule = self.get_endpoint_rule(endpoint)
        if endpoint_rule and user_type in endpoint_rule.user_types:
            rules.append(("endpoint", endpoint_rule))
        
        # Add global rule
        global_rule = self.get_global_rule(user_type)
        rules.append(("global", global_rule))
        
        return rules
    
    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled"""
        return self.enabled
    
    def get_user_type_from_request(self, request_info: Dict) -> UserType:
        """Determine user type from request information"""
        # Check if user is authenticated
        if not request_info.get("user_id"):
            return UserType.ANONYMOUS
        
        # Check user permissions/roles
        permissions = request_info.get("permissions", [])
        
        if "*" in permissions or "admin" in permissions:
            return UserType.ADMIN
        
        # Check if premium user (you can add your premium logic here)
        if request_info.get("is_premium", False):
            return UserType.PREMIUM
        
        return UserType.AUTHENTICATED
    
    def get_identifier(self, request_info: Dict, rule_type: str) -> str:
        """Generate identifier for rate limiting"""
        user_id = request_info.get("user_id")
        ip_address = request_info.get("ip_address", "unknown")
        endpoint = request_info.get("endpoint", "unknown")
        
        if rule_type == "endpoint":
            # Endpoint-specific rate limiting
            if user_id:
                return f"endpoint:{endpoint}:user:{user_id}"
            else:
                return f"endpoint:{endpoint}:ip:{ip_address}"
        
        elif rule_type == "global":
            # Global rate limiting
            if user_id:
                return f"global:user:{user_id}"
            else:
                return f"global:ip:{ip_address}"
        
        else:
            # Fallback
            return f"unknown:{ip_address}"
    
    def get_rate_limit_headers(self, result, rule: RateLimitRule) -> Dict[str, str]:
        """Generate rate limit headers for HTTP response"""
        if not self.include_headers:
            return {}
        
        headers = {
            "X-RateLimit-Limit": str(rule.limit),
            "X-RateLimit-Window": str(rule.window),
            "X-RateLimit-Remaining": str(max(0, rule.limit - result.current_count)),
            "X-RateLimit-Reset": str(result.reset_time),
        }
        
        if not result.allowed and result.retry_after:
            headers["Retry-After"] = str(result.retry_after)
        
        # Add dev mode indicator
        if self.dev_mode:
            headers["X-RateLimit-DevMode"] = "true"
            headers["X-RateLimit-DevMultiplier"] = str(self.dev_multiplier)
        
        return headers
    
    def toggle_dev_mode(self, enabled: bool = None, multiplier: int = None):
        """Toggle development mode on/off"""
        if enabled is not None:
            old_dev_mode = self.dev_mode
            self.dev_mode = enabled
            
            if multiplier is not None:
                self.dev_multiplier = multiplier
            
            # Reload rules with new settings
            self._endpoint_rules = self._load_endpoint_rules()
            self._global_rules = self._load_global_rules()
            
            if self.dev_mode:
                self._apply_dev_mode_multiplier()
            
            logger.info(f"🔄 Dev mode changed: {old_dev_mode} → {self.dev_mode} (multiplier: {self.dev_multiplier})")
    
    def get_dev_info(self) -> Dict[str, Any]:
        """Get development mode information"""
        return {
            "dev_mode": self.dev_mode,
            "dev_multiplier": self.dev_multiplier,
            "original_limits_multiplied": self.dev_mode and self.dev_multiplier > 1,
            "example_limits": {
                "login_limit": 5 * (self.dev_multiplier if self.dev_mode else 1),
                "chat_limit": 10 * (self.dev_multiplier if self.dev_mode else 1),
                "upload_limit": 5 * (self.dev_multiplier if self.dev_mode else 1)
            }
        }


# Global configuration instance
rate_limit_config = RateLimitConfig()