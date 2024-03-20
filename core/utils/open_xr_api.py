import json
import requests
from datetime import datetime, timedelta
from django.core.cache import cache


class OpenXRApi(object):
    """
    OPEN EXCHANGE RATE API wrapper
    """

    def __init__(self, api_key, end_point='https://openexchangerates.org/api'):
        """Constructor

        Args:
            api_key (string): A valid API key
            end_point (str, optional): OPEN EXCHANGE RATES API endpoint URL. Defaults to 'https://openexchangerates.org/api'.
        """
        self.api_key = api_key
        self.end_point = end_point

    def _request(self, request_url):
        r = requests.get(request_url)
        response = r.text
        return json.loads(response)

    def _parse_error(self, response):
        """
        Parse response for the error.
        In case if response contains error returns errorMessage otherwise return True

        Args:
            response (dict): API response dictionary

        Raises:
            Exception: API response error details message

        Returns:
            bool: True in case if response does not contains error
        """
        if 'error' in response and response['error'] == True:
            raise Exception(f'Error: {response["message"]}: {response["description"]}')
        else:
            return True

    def _parse_response(self, response):
        """
        Return exchange rates if retrieved successfully or return False

        Args:
            response (dict): API response dictionary

        Returns:
            dict or bool: A dictionary of exchange rates or False if request unsuccessful
        """
        rates = response["rates"]

        if rates:
            return {
                "rates": rates,
                "timestamp": response["timestamp"]
            }
        else:
            return False

    def _perform_request(self, request_url):
        """
        Execute request and redirect output to the parsing functions
        """
        response = self._request(request_url)
        if self._parse_error(response):
            results = self._parse_response(response)

            # Calculate cache timeout ('latest' values are updated shortly after each full hour on current plan,
            # while historic values should never change, so 24h seems suitable for them)
            if 'latest' in request_url:
                next_hour = (datetime.now() + timedelta(hours=1)).replace(microsecond=0, second=0, minute=0)
                timeout = (next_hour - datetime.now()).seconds
            else:
                timeout = 24 * 60 * 60

            cache.set(request_url, results, timeout)

            return results

    def get_exchange_rates(self, base_currency='USD', rate_date=None):
        """
        Get exchange rates for given currency and date.

        Args:
            base_currency (str, optional): The base currency, to which all exchange rates will relate to. Defaults to USD.
            rate_date (date, optional): The UTC date (YYYY-MM-DD) for exchange rate (use 'latest' if today or later or None). Defaults to None.

        Returns:
            dict: A dictionary of exchange rates or False if request unsuccessful
        """
        use_latest = rate_date is None or datetime.now().strftime('%Y-%m-%d') <= rate_date
        request_path = f"/latest.json" if use_latest else f"/historical/{rate_date}.json"
        request_url = f"{self.end_point}{request_path}?app_id={self.api_key}&base={base_currency}"

        # Check for cached rates
        cached_rates = cache.get(request_url)

        if cached_rates is not None:
            return cached_rates

        return self._perform_request(request_url)
