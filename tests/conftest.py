"""
共享测试 fixtures：JWT helper、Mock 配置
"""
import pytest
import jwt
import time
from dataclasses import dataclass
from unittest.mock import patch


# 测试用 JWT Secret (与 Config 默认值一致)
TEST_JWT_SECRET = "your-256-bit-secret-your-256-bit-secret"


def create_test_jwt(sub="user-123", name="Test User", picture="https://example.com/avatar.png",
                    expired=False, extra_claims=None):
    """生成测试用 JWT Token"""
    payload = {
        "sub": sub,
        "name": name,
        "picture": picture,
        "iat": int(time.time()),
    }
    if expired:
        payload["exp"] = int(time.time()) - 100  # 已过期
    else:
        payload["exp"] = int(time.time()) + 86400  # 24 小时有效

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
