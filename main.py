import sys
import asyncio 
from typing import List, Dict
from src.pricing_stream import Pricing_Stream
from src.oanda_service import Oanda_Service
from src.order_manager import Order_Manager
from src.trade_logger import TradeLogger  # MOVED TO TOP
from src.utils import get_user_instrument_and_position, get_stop_loss_pips


async def async_input(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)


async def cancel_limit_ainput(order_manager):
    limit_user_input = await async_input("1: [CANCEL LIMIT ORDER]")

    if limit_user_input == "1":
        cancel_limit_response = await order_manager.cancel_limit_order()
        return cancel_limit_response


async def cleanup_and_exit(pricing_stream, pricing_stream_task, logger, message=""):
    """Helper function to properly cleanup resources before exiting"""
    logger.log_session_end(message)
    
    # Stop the pricing stream
    pricing_stream.end_price_stream()
    
    # Wait for the pricing stream task to complete
    try:
        await asyncio.wait_for(pricing_stream_task, timeout=2.0)
    except asyncio.TimeoutError:
        print("Pricing stream cleanup timed out, forcing cancellation...")
        pricing_stream_task.cancel()
        try:
            await pricing_stream_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        print(f"Error during cleanup: {e}")
        pricing_stream_task.cancel()
        try:
            await pricing_stream_task
        except asyncio.CancelledError:
            pass


async def main():
    
    print("Trading Execution Engine")
    print("-"*100)

    RISK = float(input("Enter Risk for Session: "))
    primary = int(input("Primary? ([1] True or [2] False): "))

    if primary == 1:
        PRIMARY = True
    else:
        PRIMARY = False

    logger = TradeLogger()

    # Initialize the client
    client = Oanda_Service(primary=PRIMARY)

    # Fetch account balance right away (return an int)
    account_size = await client.fetch_account_balance()

    # Get the initial user input
    instrument, position = get_user_instrument_and_position()

    # Initialize the pricing stream object
    pricing_stream = Pricing_Stream(client, instrument, position, max_cache_size=30)

    # Initialize the order_manager
    order_manager = Order_Manager(client, pricing_stream, logger, account_size, RISK, instrument, position)

    # Wait for the stop loss pips input
    sl_pips = get_stop_loss_pips()
    
    # Log session start
    logger.log_session_start(account_size, instrument.upper(), position, sl_pips)

    # Start the pricing stream coroutine
    print("Starting Stream....")
    pricing_stream_task = asyncio.create_task(pricing_stream.start_price_stream())

    try:
        # Kick off user input loop
        while True:
            action_input = await async_input("1: [LIMIT ENTRY] \n2: [MARKET ENTRY] \n3: [CHANGE SL PIPS] \nENTER (1,2, or 3): ")
            action_input = action_input.strip()

            if action_input == "1":
                
                order_response = await order_manager.place_limit_order(sl_pips)

                # Check if order was filled immediately
                if 'orderFillTransaction' in order_response:
                    await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, "Order filled immediately!")
                    return

                # Race the order status and the cancel user input tasks
                check_order_status_task = asyncio.create_task(order_manager.check_order_status(), name="check_order_status")
                cancel_limit_ainput_task = asyncio.create_task(cancel_limit_ainput(order_manager), name="cancel_limit_ainput")

                done, pending = await asyncio.wait(
                    [check_order_status_task, cancel_limit_ainput_task], 
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Get the completed task
                race_response = done.pop()

                if race_response.get_name() == "cancel_limit_ainput":
                    try:
                        limit_cancelled_res = await race_response
                        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, "Limit order cancelled by user")
                        return
                    except Exception as e:
                        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, f"Error cancelling order: {e}")
                        return

                else:
                    try:
                        limit_filled_res = await race_response
                        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, "Limit order filled")
                        return
                    except Exception as e:
                        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, f"Error with order status: {e}")
                        return

            elif action_input == "2":
                
                market_order_task = asyncio.create_task(order_manager.place_market_order(sl_pips))
                order_response = await market_order_task
                
                await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, "Market order executed")
                return

            elif action_input == "3":
                sl_pips = get_stop_loss_pips()      # Get new sl pips
                continue                            # Continue to the next iteration for user_input again
            
            else:
                print("Invalid input. Please enter 1, 2, or 3.")

    except KeyboardInterrupt:
        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, "Program interrupted by user")
    except Exception as e:
        await cleanup_and_exit(pricing_stream, pricing_stream_task, logger, f"Unexpected error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Program terminated with error: {e}")
    finally:
        print("Program ended.")