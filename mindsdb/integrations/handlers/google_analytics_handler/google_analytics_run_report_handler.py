from mindsdb_sql_parser import parse_sql
from mindsdb.integrations.libs.api_handler import APIHandler
from mindsdb.utilities import log
from mindsdb.integrations.handlers.google_analytics_handler.google_analytics_tables import ConversionEventsTable
from google.analytics.data_v1beta.types import RunReportRequest, Dimension, Metric, DateRange
from mindsdb.integrations.libs.response import (
    HandlerStatusResponse as StatusResponse,
    HandlerResponse as Response,
    RESPONSE_TYPE,
)

import json
import os

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

DEFAULT_SCOPE = ['https://www.googleapis.com/auth/analytics.readonly']

logger = log.getLogger(__name__)

class GoogleAnalyticsHandler(APIHandler):
    """A class for handling connections and interactions with the Google Analytics Admin API.

    Attributes:
        credentials_file (str): The path to the Google Auth Credentials file for authentication
        and interacting with the Google Analytics API on behalf of the user.

        Scopes (List[str], Optional): The scopes to use when authenticating with the Google Analytics API.
    """

    name = 'google_analytics'

    def __init__(self, name: str, **kwargs):
        from mindsdb.integrations.handlers.google_analytics_handler.google_analytics_run_report_table import ReportTable

        print(f"=== INIT DEBUG FOR HANDLER ===")
        print(f"Handler being initialized with name: {name}")
        # print(f"Handler kwargs: {kwargs}")
        # print(f"kwargs keys: {list(kwargs.keys())}")

        super().__init__(name)
        self.page_size = 500
        self.connection_args = kwargs.get('connection_data', {})
        self.property_id = self.connection_args['property_id']
        if self.connection_args.get('credentials'):
            self.credentials_file = self.connection_args.pop('credentials')

        print(f"Connection argument: {self.connection_args}")
        print(f"Property id argument: {self.property_id}")
        print(f"=== END DEBUG FOR HANDLER ===")

        self.scopes = self.connection_args.get('scopes', DEFAULT_SCOPE)
        self.service = None
        self.is_connected = False
        conversion_events = ConversionEventsTable(self)
        self.conversion_events = conversion_events
        self._register_table('conversion_events', conversion_events)

        # self.report_table = ReportTable(self)
        self.report_table = ReportTable("report_table", self, property_id=self.property_id)
        # self.report_table = report_table
        self._register_table('report_table', self.report_table)

    def _get_creds_json(self):
        if 'credentials_file' in self.connection_args:
            if os.path.isfile(self.connection_args['credentials_file']) is False:
                raise Exception("credentials_file must be a file path")
            with open(self.connection_args['credentials_file']) as source:
                info = json.load(source)
            return info
        elif 'credentials_json' in self.connection_args:
            info = self.connection_args['credentials_json']
            if not isinstance(info, dict):
                raise Exception("credentials_json has to be dict")
            info['private_key'] = info['private_key'].replace('\\n', '\n')
            return info
        else:
            raise Exception('Connection args have to content ether credentials_file or credentials_json')
    
    def create_connection(self):
        info = self._get_creds_json()
        creds = service_account.Credentials.from_service_account_info(info=info, scopes=self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

        # return AnalyticsAdminServiceClient(credentials=creds)
        return BetaAnalyticsDataClient(credentials=creds)

    def connect(self):
        """
        Authenticate with the Google Analytics Beta API using the credential file.

        Returns
        -------
        service: object
            The authenticated Google Analytics Beta API service object.
        """
        if self.is_connected is True:
            return self.service

        self.service = self.create_connection()
        self.is_connected = True

        return self.service

    def check_connection(self) -> StatusResponse:
        """
        Check connection to the handler.

        Returns
        -------
        response
            Status confirmation
        """
        response = StatusResponse(False)

        try:
            # Call the Google Analytics API
            service = self.connect()
            # result = service.list_conversion_events(parent=f'properties/{self.property_id}')

            # if result is not None:
            #     response.success = True
        
            # Create a simple test request to verify connection
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[Dimension(name="date")],  # Simple dimension
                metrics=[Metric(name="activeUsers")],  # Simple metric
                date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
                limit=1  # Just get 1 row to test connection
            )
            
            # This method EXISTS on BetaAnalyticsDataClient
            result = service.run_report(request)
            
            if result is not None:
                response.success = True
                logger.info("GA4 Data API connection test successful")

        except HttpError as error:
            response.error_message = f'Error connecting to Google Analytics api: {error}.'
            log.logger.error(response.error_message)

        if response.success is False and self.is_connected is True:
            self.is_connected = False

        return response

    def native_query(self, query_string: str = None) -> Response:
        query_ast = parse_sql(query_string)
        # table = ReportTable(self, handler=self, connection_data=self.connection_args)
        # result_df = table.select(query_ast)
        result_df = self.report_table.select(query_ast)
        response = Response(RESPONSE_TYPE.TABLE, result_df)

        return response

    def get_api_url(self, endpoint):
        return f'{endpoint}/{self.property_id}'
