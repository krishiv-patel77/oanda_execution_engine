import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import csv

@dataclass
class TradeMetrics:
    """Data class to store trade execution metrics"""
    # Order Information
    order_id: str
    instrument: str
    order_type: str  # LIMIT, MARKET
    position: str    # l/s
    units: int
    
    # Pricing Information
    requested_price: Optional[float] = None
    executed_price: Optional[float] = None
    slippage_pips: Optional[float] = None
    slippage_cost: Optional[float] = None
    
    # Risk Management
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    stop_loss_pips: float = 0.0
    risk_reward_ratio: float = 2.0
    
    # Execution Metrics
    execution_time_ms: float = 0.0
    order_start_time: str = ""
    order_fill_time: str = ""
    
    # Costs
    spread_cost: float = 0.0
    commission: float = 0.0
    financing: float = 0.0
    
    # Account Impact
    account_balance_before: float = 0.0
    account_balance_after: float = 0.0
    margin_required: float = 0.0
    
    # Status
    status: str = "PENDING"  # PENDING, FILLED, CANCELLED
    fill_reason: str = ""
    
    def calculate_slippage(self, pip_value: float):
        """Calculate slippage in pips and cost"""
        if self.requested_price and self.executed_price:
            price_diff = abs(self.executed_price - self.requested_price)
            self.slippage_pips = price_diff / pip_value
            self.slippage_cost = price_diff * abs(self.units)


class TradeLogger:
    """Comprehensive logging system for trade execution"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup different log files
        self.setup_loggers()
        
        # CSV file for trade history
        self.csv_file = self.log_dir / f"trade_history_{datetime.now().strftime('%Y%m%d')}.csv"
        self.ensure_csv_headers()
    
    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        
        # Main trade logger
        self.trade_logger = logging.getLogger('trade_execution')
        self.trade_logger.setLevel(logging.INFO)
        
        # Console handler with custom formatting
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(
            self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add handlers
        self.trade_logger.addHandler(console_handler)
        self.trade_logger.addHandler(file_handler)
        
        # Prevent duplicate logs
        self.trade_logger.propagate = False
    
    def ensure_csv_headers(self):
        """Ensure CSV file has proper headers"""
        if not self.csv_file.exists():
            headers = [
                'timestamp', 'order_id', 'instrument', 'order_type', 'position',
                'units', 'requested_price', 'executed_price', 'slippage_pips',
                'slippage_cost', 'stop_loss_price', 'take_profit_price',
                'execution_time_ms', 'spread_cost', 'commission', 'financing',
                'account_balance_after', 'margin_required', 'status', 'fill_reason'
            ]
            
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def log_order_placement(self, metrics: TradeMetrics):
        """Log order placement details"""
        self.trade_logger.info("="*80)
        self.trade_logger.info("ORDER PLACEMENT")
        self.trade_logger.info("="*80)
        self.trade_logger.info(f"Order ID: {metrics.order_id}")
        self.trade_logger.info(f"Instrument: {metrics.instrument}")
        self.trade_logger.info(f"Position: {'LONG' if metrics.position == 'l' else 'SHORT'}")
        self.trade_logger.info(f"Units: {metrics.units:,}")
        self.trade_logger.info(f"Order Type: {metrics.order_type}")
        
        if metrics.requested_price:
            self.trade_logger.info(f"Requested Price: {metrics.requested_price:.5f}")
        
        self.trade_logger.info(f"Stop Loss: {metrics.stop_loss_price:.5f} ({metrics.stop_loss_pips} pips)")
        self.trade_logger.info(f"Take Profit: {metrics.take_profit_price:.5f} ({metrics.stop_loss_pips * 2} pips)")
        self.trade_logger.info(f"Risk/Reward: 1:{metrics.risk_reward_ratio}")
        self.trade_logger.info("-"*80)
    
    def log_order_execution(self, metrics: TradeMetrics, pip_value: float):
        """Log order execution details with slippage calculation"""
        # Calculate slippage
        metrics.calculate_slippage(pip_value)
        
        self.trade_logger.info("ORDER EXECUTION")
        self.trade_logger.info("="*80)
        self.trade_logger.info(f"Status: {metrics.status}")
        self.trade_logger.info(f"Executed Price: {metrics.executed_price:.5f}")
        self.trade_logger.info(f"Execution Time: {metrics.execution_time_ms:.2f}ms")
        self.trade_logger.info(f"Fill Time: {metrics.order_fill_time}")
        
        # Slippage Information
        if metrics.slippage_pips is not None:
            slippage_status = "[GOOD | BELOW 0.5 PIPS]" if metrics.slippage_pips <= 0.5 else "[BAD | ABOVE 1 PIP]" if metrics.slippage_pips <= 1.0 else "❌"
            self.trade_logger.info(f"{slippage_status} Slippage: {metrics.slippage_pips:.2f} pips (${metrics.slippage_cost:.2f})")
        
        # Cost Breakdown
        self.trade_logger.info("-" * 40)
        self.trade_logger.info("COST BREAKDOWN")
        self.trade_logger.info("-" * 40)
        self.trade_logger.info(f"Spread Cost: ${metrics.spread_cost:.2f}")
        self.trade_logger.info(f"Commission: ${metrics.commission:.2f}")
        self.trade_logger.info(f"Financing: ${metrics.financing:.2f}")
        total_cost = metrics.spread_cost + metrics.commission + abs(metrics.financing)
        if metrics.slippage_cost:
            total_cost += metrics.slippage_cost
        self.trade_logger.info(f"Total Cost: ${total_cost:.2f}")
        
        # Account Impact
        self.trade_logger.info("-" * 40)
        self.trade_logger.info("ACCOUNT IMPACT")
        self.trade_logger.info("-" * 40)
        self.trade_logger.info(f"Account Balance: ${metrics.account_balance_after:,.2f}")
        self.trade_logger.info(f"Margin Required: ${metrics.margin_required:,.2f}")
        
        self.trade_logger.info("="*80)
        
        # Save to CSV
        self.save_to_csv(metrics)
    
    def log_order_cancellation(self, order_id: str, reason: str = "User requested"):
        """Log order cancellation"""
        self.trade_logger.warning("="*80)
        self.trade_logger.warning("ORDER CANCELLED")
        self.trade_logger.warning("="*80)
        self.trade_logger.warning(f"Order ID: {order_id}")
        self.trade_logger.warning(f"Reason: {reason}")
        self.trade_logger.warning(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.trade_logger.warning("="*80)
    
    def log_error(self, error_msg: str, order_id: str = None):
        """Log execution errors"""
        self.trade_logger.error("="*80)
        self.trade_logger.error("EXECUTION ERROR")
        self.trade_logger.error("="*80)
        if order_id:
            self.trade_logger.error(f"Order ID: {order_id}")
        self.trade_logger.error(f"Error: {error_msg}")
        self.trade_logger.error(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.trade_logger.error("="*80)
    
    def log_session_start(self, account_balance: float, instrument: str, position: str, sl_pips: float):
        """Log trading session start"""
        self.trade_logger.info("TRADING SESSION STARTED")
        self.trade_logger.info("="*80)
        self.trade_logger.info(f"Account Balance: ${account_balance:,.2f}")
        self.trade_logger.info(f"Instrument: {instrument}")
        self.trade_logger.info(f"Position: {'LONG' if position == 'l' else 'SHORT'}")
        self.trade_logger.info(f"Stop Loss: {sl_pips} pips")
        self.trade_logger.info(f"Session Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.trade_logger.info("="*80)
    
    def log_session_end(self, reason: str = "Session completed"):
        """Log trading session end"""
        self.trade_logger.info("="*80)
        self.trade_logger.info("TRADING SESSION ENDED")
        self.trade_logger.info("="*80)
        self.trade_logger.info(f"Reason: {reason}")
        self.trade_logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.trade_logger.info("="*80)
    
    def log_mt5_metrics(self, units, take_profit_price, stop_loss_price, position):
        self.trade_logger.info("MT5 METRICS")
        self.trade_logger.info("="*80)
        self.trade_logger.info(f"Units: {units}")
        self.trade_logger.info(f"Take Profit: {take_profit_price}")
        self.trade_logger.info(f"Stop Loss: {stop_loss_price}")
        self.trade_logger.info(f"Position: {'BUY' if position == 'l' else 'SELL'}")
        self.trade_logger.info("="*80)


    def save_to_csv(self, metrics: TradeMetrics):
        """Save trade metrics to CSV file"""
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    metrics.order_id,
                    metrics.instrument,
                    metrics.order_type,
                    metrics.position,
                    metrics.units,
                    metrics.requested_price,
                    metrics.executed_price,
                    metrics.slippage_pips,
                    metrics.slippage_cost,
                    metrics.stop_loss_price,
                    metrics.take_profit_price,
                    metrics.execution_time_ms,
                    metrics.spread_cost,
                    metrics.commission,
                    metrics.financing,
                    metrics.account_balance_after,
                    metrics.margin_required,
                    metrics.status,
                    metrics.fill_reason
                ]
                writer.writerow(row)
        except Exception as e:
            self.trade_logger.error(f"Failed to save to CSV: {e}")
    
    def create_trade_metrics_from_response(self, order_response: Dict[str, Any], 
                                         order_type: str, position: str, 
                                         requested_price: Optional[float] = None,
                                         execution_time_ms: float = 0.0,
                                         account_balance_before: float = 0.0) -> TradeMetrics:
        """Create TradeMetrics object from OANDA API response"""
        
        # Extract order creation info
        order_create = order_response.get('orderCreateTransaction', {})
        order_fill = order_response.get('orderFillTransaction', {})
        
        metrics = TradeMetrics(
            order_id=order_create.get('id', ''),
            instrument=order_create.get('instrument', ''),
            order_type=order_type,
            position=position,
            units=int(order_create.get('units', 0)),
            requested_price=requested_price,
            stop_loss_price=float(order_create.get('stopLossOnFill', {}).get('price', 0)),
            take_profit_price=float(order_create.get('takeProfitOnFill', {}).get('price', 0)),
            execution_time_ms=execution_time_ms,
            account_balance_before=account_balance_before,
            order_start_time=order_create.get('time', ''),
        )
        
        # If order was filled, extract fill info
        if order_fill:
            metrics.executed_price = float(order_fill.get('price', 0))
            metrics.order_fill_time = order_fill.get('time', '')
            metrics.spread_cost = float(order_fill.get('halfSpreadCost', 0))
            metrics.commission = float(order_fill.get('commission', 0))
            metrics.financing = float(order_fill.get('financing', 0))
            metrics.account_balance_after = float(order_fill.get('accountBalance', 0))
            
            trade_opened = order_fill.get('tradeOpened', {})
            if trade_opened:
                metrics.margin_required = float(trade_opened.get('initialMarginRequired', 0))
            
            metrics.status = "FILLED"
            metrics.fill_reason = order_fill.get('reason', '')
        
        return metrics