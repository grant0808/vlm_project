import io
import sys
import pandas as pd
from typing import Dict, Any, List
import httpx

class TAGController:
    """
    Table/Tool-Augmented Generation (TAG) Controller.
    Translates tabular queries into executable Python (Pandas) code or calls external tools.
    """
    @staticmethod
    def execute_pandas_code(code: str, df_dict: Dict[str, pd.DataFrame]) -> str:
        """
        Safely execute dynamically generated pandas code inside a local context
        and capture stdout.
        """
        print(f"[TAG] Executing generated Python/Pandas code:\n{code}")
        
        # Capture stdout
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        
        # Create execution environment containing dataframes
        local_env = {**df_dict, "pd": pd}
        
        try:
            # Execute code block
            # In production, use restricted sandboxing for security
            exec(code, {}, local_env)
            sys.stdout = old_stdout
            output = redirected_output.getvalue()
            return output if output else "Code executed successfully with no print output."
        except Exception as e:
            sys.stdout = old_stdout
            return f"Error executing generated code: {str(e)}"

    @staticmethod
    async def call_external_api(tool_name: str, params: Dict[str, Any]) -> str:
        """
        Mock executor for external API tools (e.g. Stock Prices, Weather, CRM data).
        """
        print(f"[TAG] Executing tool '{tool_name}' with parameters: {params}")
        
        if tool_name == "get_weather":
            location = params.get("location", "Seoul")
            async with httpx.AsyncClient() as client:
                # Simulated api call or real endpoint
                return f"Weather in {location}: 24°C, Partly Cloudy, Humidity 60%."
                
        elif tool_name == "get_stock_price":
            ticker = params.get("ticker", "AAPL")
            # Mock stock data
            return f"Stock Price for {ticker}: $182.30 (+1.25%)."
            
        else:
            return f"Tool '{tool_name}' is not registered."

    @staticmethod
    def identify_tabular_query(query: str) -> bool:
        """
        Analyze if the query requires table operations (e.g. average, sum, correlation, grouping).
        """
        tabular_keywords = ["table", "df", "average", "sum", "mean", "min", "max", "excel", "csv", "statistics"]
        return any(keyword in query.lower() for keyword in tabular_keywords)
