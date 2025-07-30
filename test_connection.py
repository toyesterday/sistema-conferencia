import psycopg2
import sys

def test_supabase_connection():
    try:
        # Tentar conectar ao Supabase
        conn = psycopg2.connect(
            host="db.gpdusrhokctnctteocjw.supabase.co",
            database="postgres",
            user="postgres",
            password="937146",
            port="5432"
        )
        print("✅ Conexão com Supabase estabelecida com sucesso!")
        
        # Testar uma consulta simples
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Versão do PostgreSQL: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)

