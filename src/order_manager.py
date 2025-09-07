from src.oanda_service import Oanda_Service
from src.pricing_stream import Pricing_Stream
from src.utils import calculate_position_size, calculate_tp_sl_prices
from src.trade_logger import TradeLogger, TradeMetrics  # Import the new logging system
import json
import os
import time
import asyncio
from enum import Enum


with open(os.path.join(".", "config.json"), "r") as f:
    config = json.load(f)


class OrderStatus(Enum):
    PENDING = 'PENDING'
    CANCELLED = 'CANCELLED'
    FILLED = 'FILLED'
    NONE = 'NONE'

class OrderCancelledException(Exception):

    def __init__(self, order_details, message: str = "Order has been cancelled"):

        self.order_details = order_details
        self.message = f"{message}: \n {order_details}"

        super().__init__(self.message)


class Order_Manager:

    def __init__ (self, 
                  client: Oanda_Service, 
                  price_stream: Pricing_Stream,
                  logger: TradeLogger, 
                  account_size: float,
                  risk: float, 
                  instrument: str, 
                  position: str):


        self.client = client
        self.pricing_stream = price_stream
        self.account_size = account_size
        self.risk = risk
        self.instrument = config["INSTRUMENTS"][instrument]["symbol"]           # Get valid oanda instrument
        self.position = position
        
        # Use instrument to initialize these metrics
        self.precision = config["INSTRUMENTS"][instrument]["precision"]
        self.pip_value = config["INSTRUMENTS"][instrument]["pip_value"]

        # Track order placement
        self.order_id = None
        self.order_status = OrderStatus.NONE

        # Initialize logger
        self.logger = logger

        # Metrics for order placement
        self.metrics = {
            'order_start_time': 0,
            'order_execution_time': 0
        }


    async def place_limit_order(self, sl_pips):

        # Start the timer
        self.metrics['order_start_time'] = time.perf_counter()

        # Get current price
        current_price = await self.pricing_stream.get_current_price()

        # Calculate position size
        units = calculate_position_size(self.account_size, self.instrument, self.risk, self.position, sl_pips, self.pip_value)

        # Calculate tp and sl prices
        tp_price, sl_price = calculate_tp_sl_prices(self.position, current_price, sl_pips, self.pip_value, self.precision)

        # Place the order
        order_response = await self.client.place_limit_order(self.instrument, current_price, units, tp_price, sl_price)

        # End the timer
        self.metrics['order_execution_time'] = (time.perf_counter() - self.metrics['order_start_time']) * 1000  # Convert to ms

        # Update the order id
        self.order_id = str(order_response["orderCreateTransaction"]["id"])

        # Create trade metrics and log the order
        trade_metrics = self.logger.create_trade_metrics_from_response(
            order_response=order_response,
            order_type="LIMIT",
            position=self.position,
            requested_price=current_price,
            execution_time_ms=self.metrics['order_execution_time'],
            account_balance_before=self.account_size
        )
        
        # Log order placement
        self.logger.log_order_placement(trade_metrics)
        
        # If order was filled immediately, log execution
        if 'orderFillTransaction' in order_response:
            self.logger.log_order_execution(trade_metrics, self.pip_value)

        # Return the response
        return order_response
    

    async def check_order_status(self):

        """ This will continually check the order status after the order is placed to ensure it has been filled. """

        while self.order_status != OrderStatus.FILLED:

            # Fetch order details
            order_details = await self.client.get_order_details(self.order_id)

            # Get the state of the order
            state = order_details["order"]["state"]

            if state == "PENDING":
                self.order_status = OrderStatus.PENDING

            if state == "CANCELLED":
                self.order_status = OrderStatus.CANCELLED
                self.logger.log_order_cancellation(self.order_id, "Order cancelled by broker")
                raise OrderCancelledException(order_details)

            if state == "FILLED":
                self.order_status = OrderStatus.FILLED
                
                # Log the filled order (need to reconstruct metrics from order details)
                # This is a simplified version - you might want to store the original metrics
                self.logger.log_order_execution(
                    self._create_metrics_from_order_details(order_details), 
                    self.pip_value
                )
                
                return order_details

            await asyncio.sleep(1)        # Sleep for 1 second before checking again


    async def place_market_order(self, sl_pips):

        try:
            # Start the timer
            self.metrics['order_start_time'] = time.perf_counter()

            # Get current price
            current_price = await self.pricing_stream.get_current_price()

            # Calculate position size
            units = calculate_position_size(
                self.account_size,
                self.instrument,
                self.risk,
                self.position,
                sl_pips,
                self.pip_value
            )

            # Calculate tp and sl prices
            tp_price, sl_price = calculate_tp_sl_prices(
                self.position,
                current_price,
                sl_pips,
                self.pip_value,
                self.precision
            )

            # Place the order
            order_response = await self.client.place_market_order(
                self.instrument, units, tp_price, sl_price
            )

            # End the timer
            self.metrics['order_execution_time'] = (time.perf_counter() - self.metrics['order_start_time']) * 1000  # Convert to ms

            # Update the order id
            self.order_id = str(order_response["orderCreateTransaction"]["id"])

            # Create trade metrics and log the order
            trade_metrics = self.logger.create_trade_metrics_from_response(
                order_response=order_response,
                order_type="MARKET",
                position=self.position,
                requested_price=None,  # Market orders don't have requested price
                execution_time_ms=self.metrics['order_execution_time'],
                account_balance_before=self.account_size
            )
            
            # Log order placement and execution (market orders are typically filled immediately)
            self.logger.log_order_placement(trade_metrics)
            self.logger.log_order_execution(trade_metrics, self.pip_value)

            # Return the response
            return order_response

        except Exception as e:
            self.logger.log_error(f"Exception in place_market_order: {str(e)}", self.order_id)
            raise

    
    async def cancel_limit_order(self):
        """Cancel the current limit order"""
        
        if not self.order_id:
            return "No order to cancel"
        
        try:
            cancel_response = await self.client.cancel_order(self.order_id)
            self.order_status = OrderStatus.CANCELLED
            self.logger.log_order_cancellation(self.order_id, "User requested cancellation")
            return cancel_response
        except Exception as e:
            error_msg = f"Error cancelling order: {e}"
            self.logger.log_error(error_msg, self.order_id)
            return error_msg
    
    def _create_metrics_from_order_details(self, order_details):
        """Helper method to create basic metrics from order details"""
        order = order_details.get("order", {})
        
        metrics = TradeMetrics(
            order_id=order.get("id", ""),
            instrument=order.get("instrument", ""),
            order_type=order.get("type", ""),
            position=self.position,
            units=int(order.get("units", 0)),
            executed_price=float(order.get("price", 0)),
            stop_loss_price=float(order.get("stopLossOnFill", {}).get("price", 0)),
            take_profit_price=float(order.get("takeProfitOnFill", {}).get("price", 0)),
            status="FILLED",
            fill_reason="LIMIT_ORDER"
        )
        
        return metrics