import sqlite3

def init_db():
    with sqlite3.connect('classificacoes.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                reclamacao TEXT NOT NULL,
                motivo TEXT,
                submotivo TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, session_id)
            )
        ''')
        conn.commit()

if __name__ == "__main__":
    init_db()