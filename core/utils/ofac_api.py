import json
import requests


class OfacApi(object):
    """
    OFAC v3 API wrapper
    """

    def __init__(self, api_key,
                 min_score=95,
                 end_point='https://search.ofac-api.com/v3'):
        """Constructor

        Args:
            api_key (string): A valid OFAC API key
            min_score (int, optional): The threshold minimum for record scores to include in results set. Defaults to 95.
            end_point (str, optional): OFAC API endpoint URL. Defaults to 'https://search.ofac-api.com/v3'.
        """
        self.min_score = min_score
        self.end_point = end_point
        self.api_key = api_key
        self.request = {}
        self.search_name = None
        self.request.update({
            "apiKey": self.api_key,
            "includeAlias": 'false',
            "includeID": 'false',
            "informalName": 'true',
            "minScore": self.min_score,
            "format": "string",
            "source": [
                "SDN", "NONSDN", "PEP", "DPL", "UN", "UK", "EU", "DFAT"
            ],
        })

    def _request(self):
        r = requests.post(self.end_point, json=self.request)
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
        if response['error'] == True:
            raise Exception(f'Error: {response["errorMessage"]}')
        else:
            return True

    def _parse_response(self, response):
        """
        Return searched object details if it exists in response
        or return False

        Args:
            response (dict): API response dictionary

        Returns:
            dict or bool: Searched object details if it exists in OFAC or False
        """
        matches = response["matches"]
        search_result = matches.get(self.search_name, None)
        if search_result:
            return search_result
        else:
            return False

    def _perform_request(self):
        """
        Execute request and redirect output to the parsing functions
        """
        response = self._request()
        if self._parse_error(response):
            return self._parse_response(response)

    def search_by_name(self, search_name, target_type):
        """
        Search someone in the OFAC database by naame

        Args:
            search_name (string): Search target name
            target_type (string): Search target type (Entity, Individual or Vessel)
            
        Returns:
            dict or bool: Searched object details if it exists in OFAC or False
        """
        self.search_name = search_name
        data = {
            "type": [target_type],
            "cases": [{
                "type": target_type,
                "name": search_name
            }]
        }
        self.request.update(data)
        return self._perform_request()
