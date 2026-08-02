"""Google OAuth 2.0 authentication for Google Drive."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from utils import CREDENTIALS_PATH, TOKEN_PATH

logger = logging.getLogger("3D Print Uploader")

# Full Drive access is required for upload, folder selection, and sharing.
SCOPES = ["https://www.googleapis.com/auth/drive"]


class AuthenticationError(Exception):
    """Raised when Google OAuth authentication fails."""


class GoogleAuth:
    """Manage Google OAuth credentials and Drive service creation."""

    def __init__(
        self,
        credentials_path=CREDENTIALS_PATH,
        token_path=TOKEN_PATH,
        scopes: list[str] | None = None,
    ) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._scopes = scopes or SCOPES
        self._credentials: Optional[Credentials] = None

    @property
    def is_authenticated(self) -> bool:
        """Return True if valid credentials are loaded."""
        return self._credentials is not None and self._credentials.valid

    @property
    def credentials(self) -> Optional[Credentials]:
        return self._credentials

    @property
    def has_client_credentials(self) -> bool:
        """Return whether this user has imported Google OAuth client details."""
        return self._credentials_path.is_file()

    def import_client_credentials(self, source: Path) -> None:
        """Validate and install a user's Desktop OAuth client JSON file."""
        try:
            with source.open("r", encoding="utf-8") as source_file:
                data = json.load(source_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthenticationError(f"Could not read credentials JSON: {exc}") from exc

        installed = data.get("installed") if isinstance(data, dict) else None
        required = {"client_id", "client_secret", "auth_uri", "token_uri"}
        if not isinstance(installed, dict) or not required.issubset(installed):
            raise AuthenticationError(
                "This is not a Google Desktop app credentials file. In Google "
                "Cloud, create an OAuth client with application type 'Desktop app'."
            )

        try:
            self.logout()
            self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != self._credentials_path.resolve():
                shutil.copy2(source, self._credentials_path)
        except OSError as exc:
            raise AuthenticationError(
                f"Could not install Google credentials: {exc}"
            ) from exc

        logger.info("Imported Google OAuth client credentials for this user.")

    def load_credentials(self) -> Credentials:
        """
        Load saved credentials or run the OAuth flow.

        Raises:
            AuthenticationError: If credentials.json is missing or auth fails.
        """
        creds: Optional[Credentials] = None

        if self._token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self._token_path), self._scopes
                )
                logger.info("Loaded saved OAuth token.")
            except (OSError, ValueError) as exc:
                logger.warning("Could not load token: %s", exc)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed expired OAuth token.")
            except Exception as exc:
                logger.error("Token refresh failed: %s", exc)
                creds = None

        if not creds or not creds.valid:
            if not self._credentials_path.exists():
                raise AuthenticationError(
                    f"Google credentials not found at {self._credentials_path}. "
                    "Download OAuth client credentials from Google Cloud Console "
                    "and save as credentials.json in the application folder."
                )
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), self._scopes
                )
                # Use the explicit IPv4 loopback address recommended for
                # Windows desktop OAuth.  ``localhost`` can resolve through a
                # proxy, IPv6, or local security software instead of reaching
                # the listener created by google-auth-oauthlib.
                creds = flow.run_local_server(
                    host="127.0.0.1",
                    port=0,
                    timeout_seconds=300,
                )
                logger.info("OAuth login completed.")
            except Exception as exc:
                logger.error("OAuth flow failed: %s", exc)
                raise AuthenticationError(f"Google sign-in failed: {exc}") from exc

            self._save_credentials(creds)

        self._credentials = creds
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Persist credentials to token.json."""
        try:
            with self._token_path.open("w", encoding="utf-8") as fh:
                fh.write(creds.to_json())
            logger.debug("OAuth token saved.")
        except OSError as exc:
            logger.error("Failed to save token: %s", exc)

    def build_drive_service(self) -> Resource:
        """Return an authenticated Google Drive API v3 service."""
        creds = self.load_credentials()
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def logout(self) -> None:
        """Remove saved credentials."""
        self._credentials = None
        if self._token_path.exists():
            self._token_path.unlink()
            logger.info("Logged out; token removed.")

    def ensure_authenticated(
        self,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Resource:
        """
        Ensure the user is authenticated and return a Drive service.

        Args:
            on_progress: Optional callback for status messages.
        """
        if on_progress:
            on_progress("Checking Google authentication...")
        return self.build_drive_service()
