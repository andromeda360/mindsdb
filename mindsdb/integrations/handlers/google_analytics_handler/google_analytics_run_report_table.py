import pandas as pd
from typing import List
import warnings
import traceback
import re
import os
import json
from datetime import date as dt

from mindsdb.integrations.handlers.google_analytics_handler.google_analytics_run_report_handler import GoogleAnalyticsRunReportHandler
from google.analytics.admin_v1beta import ListConversionEventsRequest
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, Dimension, Metric, DateRange, Filter, FilterExpression, FilterExpressionList
from mindsdb_sql_parser import Constant
from mindsdb_sql_parser import ast
from google.oauth2 import service_account
from mindsdb.integrations.libs.api_handler import APITable
from google.analytics.data_v1beta.types import NumericValue
from mindsdb.integrations.utilities.sql_utils import extract_comparison_conditions

DEFAULT_SCOPE = ['https://www.googleapis.com/auth/analytics.readonly']

class RunReportTable(APITable):

    def __init__ (self, name: str, handler, **kwargs):
        # print(f"=== HANDLER INIT DEBUG FOR REPORT TABLE ===")
        super().__init__(handler)
        self.handler : GoogleAnalyticsRunReportHandler = handler
        self.name = name
        self.property_id = self.handler.property_id
        # print("=== END DEBUG FOR REPORT TABLE ===")

    def _run_report_request(self, dimensions, metrics, date_range, filter_expression, property_id):
        """
        Retrieves data from the GA API given the parameters.
        
        Args:
            dimensions (List[Dimension]): List of dimensions to include in the report.
            metrics (List[Metric]): List of metrics to include in the report.
            date_range (str): Date range for the report.
            filter_expression (str): Filter expression for the report.
            property_id (str): Google Analytics property ID.

        Returns:
            result: Diciontary that contains the retireved data with dimensions as keys.
        """

        print("Connecting to GA Database.")

        client = self.handler.connect()

        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=dimensions,
            metrics=metrics,
            date_ranges=[date_range],
            dimension_filter=filter_expression
        )
        
        response = client.run_report(request)
        result = {
            tuple(d. value for d in row.dimension_values):{
                metric.name: float(metric_value.value)
                for metric, metric_value in zip(response.metric_headers, row.metric_values)
            }
            for row in response.rows
        }

        return result
    
    def validate_query_for_aggregations(self, query: ast.Select):
        """
        Validates the SQL query structure for any aggregation functions.
        
        Args:
            query (ast.Select): The parsed SQL query
            
        Raises:
            ValueError: If validation fails with a descriptive error message
        """

        query_string = str(query)

        # usingregex for more advanced cases

        agg_functions = r'\b(SUM|COUNT|AVG|MIN|MAX|STDDEV|VARIANCE|GROUP_CONCAT|STRING_AGG)\s*\('
        agg_match = re.search(agg_functions, query_string, re.IGNORECASE)
        
        if agg_match:
            func_name = agg_match.group(1).upper()
            print(f"Error reached, query_string value?: {query_string}")
            raise ValueError(
                f"Aggregation function '{func_name}' is not allowed."
            )
        
        # Detecting ANY function call with non-empty parentheses
        # Strategy: Find all function calls, then check if they have parameters
        # Word followed by '(' with content inside ')'
        
        # First, find all potential metric functions (empty parentheses) in SELECT clause
        # Extract SELECT clause (from SELECT to FROM)
        select_match = re.search(r'\bSELECT\b(.*?)\bFROM\b', query_string, re.IGNORECASE | re.DOTALL)
        
        if select_match:
            select_clause = select_match.group(1)
            
            # Find all metrics with parenthesis: word + optional whitespace + parentheses
            all_functions = re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', select_clause)
            
            for match in all_functions:
                func_name = match.group(1)
                params = match.group(2).strip()
                
                if params:
                    print(f"Error reached, found function with parameters: {match.group(0)}")
                    raise ValueError(
                        f"Function '{func_name}' has parameters inside parentheses. "
                        f"Only empty parentheses like 'metric()' are allowed in SELECT clause."
                    )

    def select(self, query: ast.Select) -> pd.DataFrame:
        """
        Gets all conversion events from google analytics property.

        Args:
            query (ast.Select): SQL query to parse.

        Returns:
            Response: Response object containing the results.
        """

        # select * from my_ga (select event_name, count(*) from report_table group by event_name)
        # query: select event_name, count(*) from report_table group by event_nam

        # 1. Interpret the query using ASTNode object to get dimensions, metrics, filters, etc
        # 2. Use RunReportRequest GA API to get the data
        # 3. Return output from above

        self.validate_query_for_aggregations(query)

        dimensions = []
        metrics = []
        
        ## PART 1:
        ## Getting all the group by fields
        grouped_fields = set()
        for col in (query.group_by or []):
            if hasattr(col, 'parts'):
                field_name = col.parts[-1]
                grouped_fields.add(field_name)
                dimensions.append(Dimension(name=field_name))
        
        ## PART 2:
        # Processing the SELECT clause
        for col in (query.targets or []):

            ## PART 2A:
            # Checking if it's a function (like SUM, COUNT, AVG)
            if hasattr(col, '__str__') and '()' in str(col):
                col_str = str(col)
                if '(' in col_str:
                    function_name = col_str.split('(')[0].strip().upper()
                    field_name = function_name.lower()
  
                    metric_info = {
                        'field_name': field_name,
                        'aggregation': function_name,
                        'ga_metric_name': field_name,
                        'is_custom_function': True,
                        'parsed_from_string': True
                    }
                        
                    if not hasattr(self, 'metric_aggregations'):
                        self.metric_aggregations = []
                    self.metric_aggregations.append(metric_info)

                    metrics.append(Metric(name=field_name))

            ## PART 2B: 
            # Handle regular fields (non-functions)
            elif hasattr(col, 'parts'):
                field_name = col.parts[-1]

                ## Basically this part of the code decides if it is a dimension or metric by checking if 
                ## the fields are in the GROUP BY clause
                if field_name not in grouped_fields:
                    print(f"Warning: {field_name} not in GROUP BY. Treating as metric.")
                    dimensions.append(Dimension(name=field_name))
        
        print(f"Final Dimensions: {[d.name for d in dimensions]}")
        print(f"Final Metrics: {[m.name for m in metrics]}")
 
        ## PART 3:
        # date_range = DateRange(start_date="2025-01-01", end_date="2025-08-01")
        date_range = DateRange(start_date = None, end_date = None)
        ## PART 4:
        # Translates SQL WHERE into GA FilterExpression
        filter_expression = None
        if query.where:
            where_conditions = extract_comparison_conditions(query.where)
            print("Where_conditions: ", where_conditions)

            index = 1
            filters = []
            for cond in where_conditions:
                if index == 1:
                    print(f"{index}st loop")
                elif index == 2:
                    print(f"{index}nd loop")
                elif index == 3:
                    print(f"{index}rd loop")
                else:
                    print(f"{index}th loop")
    
                index += 1

                print("Cond type:", type(cond))
                print("Cond value:", cond)

                operation, field, value = cond
                operation = operation.upper() # Need to do this to standardize capitalization

                ## PART 4A:
                ## Multiple values handler
                if operation == 'IN':
                    if not isinstance(value, list):
                        raise ValueError(f"IN operator requires a list of values, got {type(value)}: {value}")

                    filters.append(
                        FilterExpression(
                            filter = Filter(
                                field_name = field,
                                in_list_filter = Filter.InListFilter(values=value)
                            )
                        )
                    )

                ## PART 4B:
                elif operation == 'BETWEEN':
                    print("Date Range Start:", date_range.start_date, "End:", date_range.end_date)

                    if field.lower() in ['date', 'event_date', 'date_range']:  
                        
                        def convert_date_string(date_value):
                            if date_value == 'today':
                                return dt.today().strftime('%Y-%m-%d')
                            elif isinstance(date_value, str):
                                return date_value  # YYYY-MM-DD format needed
                            else:
                                return str(date_value)        
         
                        if isinstance(value, (list, tuple)) and len(value) == 2:
                            start_date_str = convert_date_string(value[0])
                            end_date_str = convert_date_string(value[1])
                      
                        date_range = DateRange(start_date=start_date_str, end_date=end_date_str)
                        print(f"Updated date range to: {start_date_str} - {end_date_str}")
                        
                    else:
                      
                        print(f"Needs to be in a date format")

                ## PART 4C:
                ## String handler
                elif operation == '=':
                    filters.append(
                        FilterExpression(
                            filter = Filter(
                                field_name = field,
                                string_filter = Filter.StringFilter(value=value)
                            )
                        )
                    )

                ## PART 4D: 
                elif operation in ('>', '<', '>=', '<='):
                    try:
                        value_num = float(value)  
                    except (TypeError, ValueError):
                        raise ValueError(f"Comparison {operation} requires numeric value, got: {value}")

                    filters.append(
                        FilterExpression(
                            filter=Filter(
                                field_name=field,
                                numeric_filter=Filter.NumericFilter(
                                    operation=(
                                        Filter.NumericFilter.Operation.GREATER_THAN if operation == '>' else
                                        Filter.NumericFilter.Operation.LESS_THAN if operation == '<' else
                                        Filter.NumericFilter.Operation.GREATER_THAN_OR_EQUAL if operation == '>=' else
                                        Filter.NumericFilter.Operation.LESS_THAN_OR_EQUAL
                                    ),
                                    value=NumericValue(double_value=value_num)
                                )
                            )
                        )
                    )

                else:
                    raise ValueError(f"Unsupported operator: {operation}")

            if filters:
                if len(filters) == 1:
                    filter_expression = filters[0]
                else:
                    filter_expression = FilterExpression(
                        and_group = FilterExpressionList(expressions=filters)
                    )

        property_id = self.property_id

        ## PART 5:
        # Calls GA API
        result = self._run_report_request(
            dimensions = dimensions,
            metrics = metrics,
            date_range = date_range, 
            filter_expression = filter_expression, 
            property_id = property_id, 
        )

        # Returns an empty DataFrame if none exists
        if not result:
            # return pd.DataFrame()
            col_names = [d.name for d in dimensions] + [m.name for m in metrics]
            return pd.DataFrame(columns=col_names)
        
        # Converts GA API response into a DataFrame
        df = pd.DataFrame([
            {**dict(zip([d.name for d in dimensions], dim_key)), **metrics_dict}
            for dim_key, metrics_dict in result.items()
        ])

        if hasattr(self, 'metric_aggregations'):
            for metric_info in self.metric_aggregations:
                field_name = metric_info['field_name']
                agg_func = metric_info['aggregation']
                
                # If GA didn't handle the aggregation the way we wanted,
                # we can post-process the DataFrame
                if agg_func == 'SUM' and len(dimensions) > 0:
                    dimension_cols = [d.name for d in dimensions]
                    df = df.groupby(dimension_cols).agg({
                        field_name: 'sum'
                    }).reset_index()

        return df

    def insert(self, query: ast.Insert):
        """
        Inserts a conversion event into your GA4 property.

        Args:
            query (ast.Insert): SQL query to parse.
        """
       
        raise NotImplementedError

    def update(self, query: ast.Update):
        """
        Updates a conversion event into your GA4 property.

        Args:
            query (ast.Update): SQL query to parse.
        """
        
        raise NotImplementedError

    def delete(self, query: ast.Delete):
        """
        Deletes a conversion event into your GA4 property.

        Args:
            query (ast.Delete): SQL query to parse.
        """

        raise NotImplementedError

