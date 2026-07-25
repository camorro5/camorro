#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instagram API endpoints and handlers."""

import json
import time
import requests
from .session import Session


class InstagramAPI:
    """Handles Instagram API communication."""

    # Login endpoints
    LOGIN_URL = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"

    # Other useful endpoints
    CHECK_USERNAME = "https://i.instagram.com/api/v1/accounts/check_username/"
    SEND_RECOVERY = "https://www.instagram.com/api/v1/accounts/send_recovery_flow_email/"
    PASSWORD_RESET = "https://www.instagram.com/api/v1/accounts/account_recovery_send_ajax/"

    def __init__(self, proxy=None):
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._session = requests.Session()

    # ── Login attempt ─────────────────────────────────

    def try_login(self, username, password):
        """
        Attempts Instagram login.
        Returns dict with:
            - success (bool)
            - status (str): 'valid' / 'invalid' / 'checkpoint' / 'error'
            - message (str)
        """
        headers = Session.build_headers()
        payload = Session.build_login_payload(username, password)

        try:
            r = self._session.post(
                self.LOGIN_URL,
                data=payload,
                headers=headers,
                proxies=self.proxy,
                timeout=20,
            )

            text = r.text
            status = r.status_code

            # Parse response
            try:
                resp = json.loads(text)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "status": "parse_error",
                    "message": f"Could not parse response (HTTP {status})",
                    "http_status": status,
                }

            # Check result
            if resp.get("authenticated") is True:
                return {
                    "success": True,
                    "status": "valid",
                    "message": "Login successful!",
                    "user_id": resp.get("userId"),
                }

            # Checkpoint / 2FA
            if "checkpoint_required" in text or resp.get("checkpoint_url"):
                return {
                    "success": False,
                    "status": "checkpoint",
                    "message": "Password may be correct but checkpoint/2FA is required",
                }

            # Check specific error messages
            message = resp.get("message", "").lower()
            if "password" in message and "incorrect" in message:
                return {
                    "success": False,
                    "status": "invalid",
                    "message": "Incorrect password",
                }
            elif "user" in message and ("not found" in message or "doesn't exist" in message):
                return {
                    "success": False,
                    "status": "invalid_user",
                    "message": "Username not found",
                }
            elif "too many" in message or "rate" in message:
                return {
                    "success": False,
                    "status": "rate_limited",
                    "message": "Rate limited — slow down",
                }
            elif "challenge" in message:
                return {
                    "success": False,
                    "status": "challenge",
                    "message": "Challenge required",
                }
            else:
                return {
                    "success": False,
                    "status": "unknown",
                    "message": message or f"Unknown response (HTTP {status})",
                    "raw": text[:500],
                }

        except requests.exceptions.Timeout:
            return {"success": False, "status": "timeout", "message": "Request timed out"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status": "connection_error", "message": "Connection failed (check proxy?)"}
        except Exception as e:
            return {"success": False, "status": "error", "message": str(e)}

    # ── Profile check ──────────────────────────────────

    def profile_exists(self, username):
        """Check if an Instagram profile exists."""
        headers = Session.build_headers()
        try:
            r = self._session.get(
                f"https://www.instagram.com/{username}/",
                headers=headers,
                proxies=self.proxy,
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return None
