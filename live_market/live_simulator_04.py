import tkinter as tk
import threading
import queue
import pandas as pd
import json
import os
from logzero import logger
from web_req import sws


#sample start

# Simulated external function to update live prices
def on_data(wsapp,message):
    try:
        LTP={}
        LTP[message['token']]= {'token' : message['token'],'ltp':message['last_traded_price']/100}
        live=(LTP['11536']['ltp'])
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        price_queue.put((live, timestamp))

    except Exception as e:
           print(e)

def on_open(wsapp):
        logger.info("on open")
        token_list = [{"exchangeType": 1,"tokens": ["11536"]}]
        mode=1
        correlation_id="abc123"
        sws.subscribe(correlation_id, mode, token_list)
        #print('below_sub')
        #sws.unsubscribe(correlation_id, mode, token_list)

def on_error(wsapp, error):
        logger.error(error)

def on_close(wsapp):
        logger.info("Close")
def close_connection():
        sws.close_connection()

sws.on_open =  on_open
sws.on_data =  on_data
sws.on_error = on_error
sws.on_close = on_close


class StockSimulatorApp:
    def __init__(self, root, price_queue):
        self.root = root
        self.root.title("Stock Simulator_with_live_Price")
        self.root.config(bg="orange")

        self.price_queue = price_queue
        self.current_cash = 1000000
        self.holdings = {}
        self.latest_price = 0
        self.trade_history_file = "trade_history_04.json"
        
        self.setup_ui()
        self.load_trade_history()
        self.update_price()

    def setup_ui(self):
        # Wallet Frame
        self.wallet_frame = tk.Frame(self.root, bg="black")
        self.wallet_frame.pack(pady=10)

        self.cash_label = tk.Label(self.wallet_frame, text=f"Cash: ${self.current_cash:.2f}", font=("Helvetica", 14), bg="black", fg="white")
        self.cash_label.pack(pady=5)

        # Price Frame
        self.price_label = tk.Label(self.root, text="", font=("Helvetica", 18), fg="white", bg="black")
        self.price_label.pack(pady=10)

        # Holding Frame
        self.holding_frame = tk.Frame(self.root, bg="black")
        self.holding_frame.pack(pady=10)

        self.holding_label = tk.Label(self.holding_frame, text="Holdings:", font=("Helvetica", 14), bg="black", fg="white")
        self.holding_label.pack(pady=5)

        self.holding_listbox = tk.Listbox(self.holding_frame, font=("Helvetica", 12), width=50, bg="white", fg="white")
        self.holding_listbox.pack(pady=5)

        # Quantity Entry
        self.quantity_label = tk.Label(self.root, text="Quantity:", font=("Helvetica", 14), bg="black", fg="white")
        self.quantity_label.pack(pady=5)

        self.quantity_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.quantity_entry.pack(pady=5)

        # Buy/Sell Buttons
        self.button_frame = tk.Frame(self.root, bg="black")
        self.button_frame.pack(pady=20)

        self.buy_button = tk.Button(self.button_frame, text="Buy", font=("Helvetica", 14), command=self.buy_share, bg="green", fg="white")
        self.buy_button.pack(side=tk.LEFT, padx=20)

        self.sell_button = tk.Button(self.button_frame, text="Sell", font=("Helvetica", 14), command=self.sell_share, bg="red", fg="white")
        self.sell_button.pack(side=tk.RIGHT, padx=20)

        # Add Money Entry and Button
        self.add_money_label = tk.Label(self.root, text="Add Money:", font=("Helvetica", 14), bg="black", fg="white")
        self.add_money_label.pack(pady=5)

        self.add_money_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.add_money_entry.pack(pady=5)

        self.add_money_button = tk.Button(self.root, text="Add", font=("Helvetica", 14), command=self.add_money, bg="blue", fg="white")
        self.add_money_button.pack(pady=10)

    def update_price(self):
        try:
            self.latest_price, timestamp = self.price_queue.get_nowait()
            self.price_label.config(text=f"Current Price: ${self.latest_price:.2f} (Updated at: {timestamp})")
            self.update_holdings()
        except queue.Empty:
            pass
        self.root.after(10, self.update_price)

    def buy_share(self):
        try:
            quantity = int(self.quantity_entry.get())
            if self.current_cash >= self.latest_price * quantity:
                self.current_cash -= self.latest_price * quantity
                if self.latest_price in self.holdings:
                    self.holdings[self.latest_price] += quantity
                else:
                    self.holdings[self.latest_price] = quantity
                self.cash_label.config(text=f"Cash: ${self.current_cash:.2f}")
                self.update_holdings()
                self.save_trade_history()
        except ValueError:
            pass

    def sell_share(self):
        try:
            quantity = int(self.quantity_entry.get())
            if self.holdings:
                buy_price = float(next(iter(self.holdings)))
                if self.holdings[buy_price] > quantity:
                    self.holdings[buy_price] -= quantity
                else:
                    del self.holdings[buy_price]
                self.current_cash += self.latest_price * quantity
                self.cash_label.config(text=f"Cash: ${self.current_cash:.2f}")
                self.update_holdings()
                self.save_trade_history()
        except ValueError:
            pass

    def add_money(self):
        try:
            amount = float(self.add_money_entry.get())
            self.current_cash += amount
            self.cash_label.config(text=f"Cash: ${self.current_cash:.2f}")
            self.save_trade_history()
        except ValueError:
            pass

    def update_holdings(self):
        self.holding_listbox.delete(0, tk.END)
        for price, quantity in self.holdings.items():
            pnl = (self.latest_price - price) * quantity
            color = "green" if pnl >= 0 else "red"
            self.holding_listbox.insert(tk.END, f"Buy Price: ${price:.2f}, Quantity: {quantity}, PnL: ${pnl:.2f}")
            self.holding_listbox.itemconfig(tk.END, {'fg': color})

    def save_trade_history(self):
        trade_history = {
            "current_cash": self.current_cash,
            "holdings": self.holdings,
        }
        with open(self.trade_history_file, 'w') as f:
            json.dump(trade_history, f)

    def load_trade_history(self):
        if os.path.exists(self.trade_history_file):
            with open(self.trade_history_file, 'r') as f:
                trade_history = json.load(f)
                self.current_cash = trade_history.get("current_cash", 1000000)
                self.holdings = {float(k): int(v) for k, v in trade_history.get("holdings", {}).items()}
                self.cash_label.config(text=f"Cash: ${self.current_cash:.2f}")
                self.update_holdings()


#start websocket function
def lo():
       sws.connect()

# Create the main window
root = tk.Tk()


# Create a queue for live price updates
price_queue = queue.Queue()


#Start the websocket in a separate thread and update live price
price_updater_thread = threading.Thread(target=lo)
price_updater_thread.daemon = True
price_updater_thread.start()


# Create the stock simulator app
app = StockSimulatorApp(root, price_queue)

# Run the application
root.mainloop()









