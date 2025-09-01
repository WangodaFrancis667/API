import requests
import json
import logging
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import StoreVersionCheck

logger = logging.getLogger(__name__)


class StoreVersionService:
    """
    Service class to fetch version information from Google Play Store and Apple App Store.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def get_google_play_version(
        self, package_id: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Fetch version information from Google Play Store.

        Args:
            package_id: Android package ID (e.g., 'com.afrobuyug.app')

        Returns:
            Tuple of (version_info_dict, error_message)
        """
        try:
            url = f"https://play.google.com/store/apps/details?id={package_id}&hl=en&gl=us"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse the HTML to extract version information
            html_content = response.text

            # Look for version information in the HTML
            # Google Play uses different patterns, we'll try multiple approaches
            version_info = self._extract_play_store_version(html_content, package_id)

            # Truncate version_name if it's too long for the database
            version_name = version_info.get("version_name")
            if version_name and len(version_name) > 200:
                version_name = version_name[:200]
                logger.warning(
                    f"Truncated long version name for {package_id}: {version_info.get('version_name')}"
                )

            # Log the successful check
            StoreVersionCheck.objects.create(
                platform="android",
                app_id=package_id,
                version_name=version_name,
                version_code=version_info.get("version_code"),
                status="success",
                response_data=version_info,
            )

            return version_info, None

        except requests.RequestException as e:
            error_msg = f"Failed to fetch Google Play Store data: {str(e)}"
            logger.error(error_msg)

            StoreVersionCheck.objects.create(
                platform="android",
                app_id=package_id,
                status="failed",
                error_message=error_msg,
            )

            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error fetching Google Play Store data: {str(e)}"
            logger.error(error_msg)

            StoreVersionCheck.objects.create(
                platform="android",
                app_id=package_id,
                status="failed",
                error_message=error_msg,
            )

            return None, error_msg

    def get_app_store_version(
        self, app_id: str, bundle_id: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Fetch version information from Apple App Store using iTunes API.

        Args:
            app_id: Apple App Store ID (can be with or without 'id' prefix)
            bundle_id: iOS bundle ID (optional, used for validation)

        Returns:
            Tuple of (version_info_dict, error_message)
        """
        try:
            # Clean the app_id - remove 'id' prefix if present
            clean_app_id = (
                app_id.replace("id", "") if app_id.startswith("id") else app_id
            )

            # Use iTunes Search API
            url = f"https://itunes.apple.com/lookup?id={clean_app_id}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data["resultCount"] == 0:
                error_msg = f"App not found in App Store with ID: {app_id}"

                StoreVersionCheck.objects.create(
                    platform="ios",
                    app_id=app_id,
                    status="not_found",
                    error_message=error_msg,
                )

                return None, error_msg

            app_info = data["results"][0]

            # Validate bundle ID if provided
            if bundle_id and app_info.get("bundleId") != bundle_id:
                error_msg = f"Bundle ID mismatch. Expected: {bundle_id}, Got: {app_info.get('bundleId')}"
                logger.warning(error_msg)

            version_info = {
                "version_name": app_info.get("version"),
                "build_number": None,  # iTunes API doesn't provide build numbers
                "bundle_id": app_info.get("bundleId"),
                "app_name": app_info.get("trackName"),
                "release_date": app_info.get("currentVersionReleaseDate"),
                "release_notes": app_info.get("releaseNotes", ""),
                "minimum_os_version": app_info.get("minimumOsVersion"),
                "app_store_url": app_info.get("trackViewUrl"),
                "icon_url": app_info.get("artworkUrl512"),
                "file_size": app_info.get("fileSizeBytes"),
                "content_rating": app_info.get("contentAdvisoryRating"),
                "raw_data": app_info,
            }

            # Truncate version_name if it's too long for the database
            version_name = version_info["version_name"]
            if version_name and len(version_name) > 200:
                version_name = version_name[:200]
                logger.warning(
                    f"Truncated long iOS version name for {app_id}: {version_info['version_name']}"
                )

            StoreVersionCheck.objects.create(
                platform="ios",
                app_id=app_id,
                version_name=version_name,
                build_number=version_info.get("build_number"),
                status="success",
                response_data=version_info,
            )

            return version_info, None

        except requests.RequestException as e:
            error_msg = f"Failed to fetch App Store data: {str(e)}"
            logger.error(error_msg)

            StoreVersionCheck.objects.create(
                platform="ios", app_id=app_id, status="failed", error_message=error_msg
            )

            return None, error_msg
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse App Store response: {str(e)}"
            logger.error(error_msg)

            StoreVersionCheck.objects.create(
                platform="ios", app_id=app_id, status="failed", error_message=error_msg
            )

            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error fetching App Store data: {str(e)}"
            logger.error(error_msg)

            StoreVersionCheck.objects.create(
                platform="ios", app_id=app_id, status="failed", error_message=error_msg
            )

            return None, error_msg

    def _extract_play_store_version(self, html_content: str, package_id: str) -> Dict:
        """
        Extract version information from Google Play Store HTML.
        This is a fallback method since Google doesn't provide a public API.
        """
        import re

        version_info = {
            "package_id": package_id,
            "version_name": None,
            "version_code": None,
            "last_updated": None,
            "app_name": None,
        }

        try:
            # Try to extract version name using various patterns
            version_patterns = [
                r'"versionName":"([^"]+)"',
                r"Current Version[^>]*>([^<]+)<",
                r"Version[^>]*>([^<]+)<",
                r">\s*(\d+\.\d+\.\d+)\s*<",
            ]

            for pattern in version_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    version_info["version_name"] = match.group(1).strip()
                    break

            # Try to extract app name
            app_name_patterns = [
                r'"name":"([^"]+)"',
                r"<title>([^<]+) - Google Play</title>",
                r'data-track-click="app-name">([^<]+)</span>',
            ]

            for pattern in app_name_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    version_info["app_name"] = match.group(1).strip()
                    break

            # Try to extract last updated date
            updated_patterns = [r"Updated[^>]*>([^<]+)<", r"Last updated[^>]*>([^<]+)<"]

            for pattern in updated_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    version_info["last_updated"] = match.group(1).strip()
                    break

        except Exception as e:
            logger.warning(f"Failed to parse Google Play Store HTML: {str(e)}")

        return version_info

    def get_alternative_play_store_info(
        self, package_id: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Alternative method to get Google Play Store info using different endpoints.
        This uses unofficial APIs that might be more reliable.
        """
        try:
            # Try using the unofficial Play Store API
            url = f"https://play.google.com/store/apps/details?id={package_id}&hl=en"

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GoogleBot/2.1; +http://www.google.com/bot.html)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            return self._extract_play_store_version(response.text, package_id), None

        except Exception as e:
            error_msg = f"Alternative Google Play fetch failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg


def get_store_service() -> StoreVersionService:
    """Factory function to get the store version service."""
    return StoreVersionService()
