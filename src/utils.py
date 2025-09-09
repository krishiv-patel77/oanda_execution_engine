import json

RR = 1

with open("config.json", "r") as f:

    config = json.load(f)


def convert_to_valid_float(instrument, precision, price):

    precise_price = round(price, precision)

    return precise_price


""" Returns the position_size which is the number of units to trade based on risk and stop_loss pips"""
def calculate_position_size(account_size, instrument, risk, position, sl_pips, pip_value):
    
    risk = float(risk)

    if "JPY" in instrument:
        pip_value = pip_value/100

    risk_amount = account_size * (risk/100)

    position_size = int(risk_amount/(sl_pips * pip_value))

    if position == "s":
        position_size *= -1

    return position_size

""" Calculates the take profit and stop loss prices based on the provided pips and current price of the instrument. """
def calculate_tp_sl_prices(position, current_price, sl_pips, pip_value, precision):
    
    tp_pips = sl_pips * RR

    sl_dist = sl_pips * pip_value
    tp_dist = tp_pips * pip_value

    if position == "s":
        sl_price = current_price + sl_dist
        tp_price = current_price - tp_dist
    else:
        sl_price = current_price - sl_dist
        tp_price = current_price + tp_dist

    sl_price = round(sl_price, precision)
    tp_price = round(tp_price, precision)

    return tp_price, sl_price


def get_user_instrument_and_position():

    instruments = config["INSTRUMENTS"]

    while True:
        # Get the instrument input
        user_instrument = input("Enter Instrument: ").upper()

        # Validate instrument
        if user_instrument not in instruments:
             print("Invalid Instrument. Try Again.")
             print(f"Valid Instruments: {[print(f"{i} -> Alias: {instrument}, Symbol: {value['symbol']}, Pip Value: {value['pip_value']} \n") 
                                         for i, (instrument, value) in enumerate(instruments.items())]}")
             continue
        
        # Get the position input
        user_position = input("Enter Position (Long -> l | Short -> s): ").strip().lower()

        # Validate position
        if user_position != "l" and user_position != "s":
             print("Invalid position. Enter l for long position and s for short position.")
             continue
        
        return user_instrument, user_position



def get_stop_loss_pips():
     
    sl_pips = float(input("Enter Stop Loss Pips: ").strip())

    return sl_pips