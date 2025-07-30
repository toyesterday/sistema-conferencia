from src.main import app, db, inicializar_banco_dados

with app.app_context():
    inicializar_banco_dados()
    print("Banco de dados inicializado com sucesso!")

