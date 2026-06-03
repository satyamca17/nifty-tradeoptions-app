import sqlite3

DB_PATH = "users.db"

def init_db():
    """Creates all necessary tables for the Options Pro application."""
    conn = sqlite3.connect(DB_PATH, timeout=10)  # Waits up to 10 seconds if locked
    cursor = conn.cursor()

    # 1. Users Table (Authentication)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            pancard TEXT NOT NULL,
            password_hash TEXT NOT NULL
        );
    ''')

    # 2. Trade History Table (Closed Positions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,          -- 'Buy' or 'Sell'
            contract TEXT NOT NULL,        -- e.g., '24000 CE'
            qty INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            pnl REAL NOT NULL,
            reason TEXT                    -- e.g., 'Target Hit', 'Manual Exit'
        );
    ''')

    # 3. Daily Profit & Loss Table (Capital Tracking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_pnl (
            record_date DATE NOT NULL,
            username TEXT NOT NULL,
            starting_capital REAL,
            realized_pnl REAL,
            ending_capital REAL,
            PRIMARY KEY (record_date, username)
        );
    ''')

    # 4. Open Positions Table (Active Trades till Expiry)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS open_positions (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            strike INTEGER NOT NULL,
            opt_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target REAL,
            sl REAL,
            quantity INTEGER NOT NULL
        );
    ''')


    # Save changes and close the connection
    conn.commit()
    conn.close()

    # Add this at the very bottom of your setup file!
if __name__ == "__main__":
        print("Initializing database...")
        init_db()
        print("Database tables created successfully!")