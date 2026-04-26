"""
安全层测试：Token 提取优先级、JWT 校验、异常处理
"""
import pytest
import jwt
import time
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from tests.conftest import TEST_JWT_SECRET, create_test_jwt


class TestExtractToken:
    """PS-01 ~ PS-02: Token 提取优先级"""

    def _make_request(self, cookies=None, headers=None):
        """构造 mock Request 对象"""
        request = MagicMock()
        request.cookies = cookies or {}
        request.headers = headers or {}
        return request

    # PS-01: Cookie 优先于 Header
    def test_cookie_takes_priority_over_header(self):
        from app.core.security import _extract_token

        cookie_token = "cookie-token-value"
        header_token = "header-token-value"

        request = self._make_request(cookies={"jwt_token": cookie_token})
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=header_token
        )

        result = _extract_token(request, credentials)
        assert result == cookie_token

    # PS-02: 无 Cookie 时用 Header
    def test_fallback_to_bearer_header(self):
        from app.core.security import _extract_token

        header_token = "header-token-value"
        request = self._make_request(cookies={})
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=header_token
        )

        result = _extract_token(request, credentials)
        assert result == header_token


class TestGetCurrentUser:
    """PS-03 ~ PS-04: JWT 校验"""

    def _make_request(self, token=None):
        request = MagicMock()
        request.cookies = {"jwt_token": token} if token else {}
        return request

    # PS-03: 有效 JWT → 返回 CurrentUser
    @patch("app.core.security.settings")
    def test_valid_jwt_returns_current_user(self, mock_settings):
        from app.core.security import get_current_user

        mock_settings.JWT_SECRET = TEST_JWT_SECRET
        token = create_test_jwt(sub="user-42", name="Alice", picture="https://pic.example.com/a.jpg")

        request = self._make_request(token=token)
        user = get_current_user(request, None)

        assert user.id == "user-42"
        assert user.name == "Alice"
        assert user.avatar == "https://pic.example.com/a.jpg"

    # PS-04: 过期 JWT → 401
    @patch("app.core.security.settings")
    def test_expired_jwt_raises_401(self, mock_settings):
        from app.core.security import get_current_user

        mock_settings.JWT_SECRET = TEST_JWT_SECRET
        token = create_test_jwt(expired=True)

        request = self._make_request(token=token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request, None)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
