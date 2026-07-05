import sqlite3
from datetime import datetime

DB_FILE = "quotes.db"

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                author TEXT,
                category TEXT,
                is_fav INTEGER DEFAULT 0,
                date TEXT,
                image_path TEXT
            )
        ''')
        self.conn.commit()

        cursor.execute("SELECT COUNT(*) FROM quotes")
        if cursor.fetchone()[0] == 0:
            examples = [
                ("Будь собой, остальные роли уже заняты.", "Оскар Уайльд", "Мотивация", 1, datetime.now().isoformat(), ""),
                ("Жизнь — это то, что с тобой происходит, пока ты строишь планы.", "Джон Леннон", "Философия", 0, datetime.now().isoformat(), ""),
                ("Единственный способ делать великую работу — любить то, что ты делаешь.", "Стив Джобс", "Мотивация", 1, datetime.now().isoformat(), ""),
            ]
            cursor.executemany(
                "INSERT INTO quotes (text, author, category, is_fav, date, image_path) VALUES (?,?,?,?,?,?)",
                examples
            )
            self.conn.commit()

    def get_all(self, category=None, fav_only=False):
        cursor = self.conn.cursor()
        query = "SELECT id, text, author, category, is_fav, date, image_path FROM quotes"
        conditions = []
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if fav_only:
            conditions.append("is_fav = 1")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY date DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_categories(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM quotes WHERE category IS NOT NULL AND category != ''")
        rows = cursor.fetchall()
        return [row["category"] for row in rows]

    def insert(self, data):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO quotes (text, author, category, is_fav, date, image_path) VALUES (?,?,?,?,?,?)",
            (data["text"], data["author"], data["category"], int(data["is_fav"]), data["date"], data["image_path"])
        )
        self.conn.commit()
        return cursor.lastrowid

    def update(self, data):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE quotes SET text=?, author=?, category=?, is_fav=?, date=?, image_path=? WHERE id=?",
            (data["text"], data["author"], data["category"], int(data["is_fav"]), data["date"], data["image_path"], data["id"])
        )
        self.conn.commit()

    def delete(self, quote_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM quotes WHERE id=?", (quote_id,))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()