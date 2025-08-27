import sqlite3
import pandas as pd

# Conectar ao banco de dados
with sqlite3.connect('classificacoes.db') as conn:
    # Executar consulta SQL
    query = "SELECT * FROM classificacoes"
    df = pd.read_sql_query(query, conn)

# Exibir os resultados
print(df)