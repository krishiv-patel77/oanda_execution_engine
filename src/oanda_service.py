import oandapyV20
import oandapyV20.endpoints.accounts as Accounts_EDPT
import oandapyV20.endpoints.orders as Orders_EDPT
import oandapyV20.endpoints.pricing as Pricing_EDPT
from typing import List
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

class Oanda_Service:
     
    def __init__(self, primary: bool):

        # Fetch sensitive information
        API_KEY = os.getenv('OANDA_API_KEY')
        if primary:
            ACCOUNT_ID = os.getenv('PRIMARY_ACCOUNT_ID')
        else:
            ACCOUNT_ID = os.getenv('SECONDARY_ACCOUNT_ID')

        # Initialize Service
        self.client = oandapyV20.API(access_token=API_KEY)
        self.account_id = ACCOUNT_ID


    async def fetch_current_price(self, instrument: str):
        """ Fetches the current market price for a given instrument """

        # Set request parameters
        params = {
            "instruments": instrument
        }

        # Initialize the request
        r = Pricing_EDPT.PricingInfo(self.account_id, params=params)

        # Run the synchronous request in a thread pool to make it async
        await asyncio.to_thread(self.client.request, r)

        # Return the response object
        return r.response


    async def fetch_account_details(self):
        """ Fetches an account summary. """

        # Initialize the request
        r = Accounts_EDPT.AccountSummary(self.account_id)

        # Run the synchronous request in a thread pool
        await asyncio.to_thread(self.client.request, r)

        # Return the response
        return r.response
    

    async def fetch_account_balance(self):
        """ Uses account details to extract and send the account balance as an integer. """

        summary = await self.fetch_account_details()
        balance = float(summary["account"]["balance"])
        return balance


    async def place_limit_order(self, instrument, price, units_to_trade, tp_price, sl_price):
        
        order_data = {
                "order": {
                    "stopLossOnFill": {
                    "timeInForce": "GTC",
                    "price": str(sl_price)
                    },
                    "takeProfitOnFill": {
                    "price": str(tp_price)
                    },
                    "timeInForce": "GTC",
                    "price": str(price),
                    "instrument": str(instrument),
                    "units": str(units_to_trade),
                    "type": "LIMIT",
                    "positionFill": "DEFAULT"
                }
            }
        
        # Create the order object
        r = Orders_EDPT.OrderCreate(self.account_id, data=order_data)

        # Place the Order (run in thread pool)
        await asyncio.to_thread(self.client.request, r)

        return r.response


    async def place_market_order(self, instrument, units_to_trade, tp_price, sl_price):
        
        order_data = {
                "order": {
                    "stopLossOnFill": {
                    "timeInForce": "GTC",
                    "price": str(sl_price)
                    },
                    "takeProfitOnFill": {
                    "price": str(tp_price)
                    },
                    "timeInForce": "FOK",
                    "instrument": str(instrument),
                    "units": str(units_to_trade),
                    "type": "MARKET",
                    "positionFill": "DEFAULT"
                }
            }
        
        # Create the order object
        r = Orders_EDPT.OrderCreate(self.account_id, data=order_data)

        # Place the Order (run in thread pool)
        await asyncio.to_thread(self.client.request, r)

        return r.response


    async def get_order_details(self, order_id: str):
        """ Returns the details including order status (PENDING, FILLED, CANCELLED, TRIGGERED) for a single order with the specified id. """
        
        r = Orders_EDPT.OrderDetails(self.account_id, order_id)

        # Run in thread pool
        await asyncio.to_thread(self.client.request, r)

        return r.response
    
    
    async def cancel_order(self, order_id):

        # Create the order object
        r = Orders_EDPT.OrderCancel(self.account_id, orderID=order_id)

        # Place the Order (run in thread pool)
        await asyncio.to_thread(self.client.request, r)

        return r.response