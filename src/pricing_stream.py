""" Our goal here is to implement a pricing stream that can append and access elements on O(1) time with efficient caching. """

from collections import deque       # Pronounced Deck and will be the data structure holding the price data due to its efficiency and speed
import time
import json
from typing import Optional
from dataclasses import dataclass
import asyncio
from src.utils import convert_to_valid_float

with open("./config.json", "r") as f:
    config = json.load(f)

""" This is the object we will append to the pricing stream and will handle the latest prices. """
@dataclass
class MarketData:
    bid: float
    ask: float
    timestamp: float
    spread: float


class Pricing_Stream():

    def __init__(self, client, instrument: str, position:str, max_cache_size: int = 30) -> None:

        self.client = client
        self.instrument = config["INSTRUMENTS"][instrument]['symbol']
        self.position = position

        self.precision = config["INSTRUMENTS"][instrument]['precision']

        self.prices = deque(maxlen=max_cache_size)          # This var will hold all the prices. Length of this will not exceed max_cache_size
        self.current_price: Optional[MarketData] = None     # Holds the current price for easy access
        self.is_streaming: bool = False                     # For checking to see if the streaming is running or not 
        

        # Performance metrics
        self.metrics = {
            'stream_start_time': 0,
            'prices_per_second': 0,
        }

    def add_price(self, bid:float, ask:float) -> None:
        """ Function to call when adding a price to the pricing stream. """

        market_data = MarketData(
            bid=bid,
            ask=ask, 
            timestamp=time.time(),
            spread= abs(bid-ask)
        )

        self.prices.append(market_data)     # Append data from the stream to the cache
        self.current_price = market_data    # Set the current price to the most recently appended market_data obj


    async def get_current_price(self) -> float:
        """ Function to access the current price for the instrument. """

        if not self.current_price:
            await self._wait_for_price_data()
        
        return self.current_price.ask if self.position == "l" else self.current_price.bid
    

    def get_spread(self) -> float:
        """ Returns the most recent spread. """

        return self.current_price.spread if self.current_price else 0.0 
    

    async def _wait_for_price_data(self, timeout: float = 10.0):
        
        """ Wait for price data to become available in the stream. """
        
        start_time = time.perf_counter()
        
        while not self.current_price:
            # Check if timeout exceeded
            if time.perf_counter() - start_time > timeout:
                raise asyncio.TimeoutError(f"No price data received within {timeout} seconds")
            
            # Use async sleep instead of blocking sleep
            await asyncio.sleep(0.1)  # Check every 100ms

    

    async def start_price_stream(self) -> None:
        """Start the price streaming coroutine"""

        self.is_streaming = True
        price_count = 0
        
        self.metrics['stream_start_time'] = time.perf_counter()
        
        try:
            while self.is_streaming:
                response = await self.client.fetch_current_price(self.instrument)
                
                bid_price = float(response['prices'][0]['bids'][0]['price'])
                ask_price = float(response['prices'][0]['asks'][0]['price'])
                
                # Convert to valid float format
                bid_price = convert_to_valid_float(self.instrument, self.precision, bid_price)
                ask_price = convert_to_valid_float(self.instrument, self.precision, ask_price)
                
                self.add_price(bid_price, ask_price)
                price_count += 1
                
                # Small sleep to prevent overwhelming the API
                await asyncio.sleep(0.01)  # 10ms
                
        except Exception as e:
            print(f"Price streaming error: {e}")

        finally:
            # Calculate prices per second
            elapsed_time = time.perf_counter() - self.metrics['stream_start_time']
            self.metrics['prices_per_second'] = price_count / elapsed_time if elapsed_time > 0 else 0


    def end_price_stream(self):

        self.is_streaming = False