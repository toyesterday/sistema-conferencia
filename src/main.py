import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"

# Tentar conectar ao Supabase primeiro, com fallback para SQLite
try:
    import psycopg2
    # Testar conexão com Supabase
    test_conn = psycopg2.connect(
        host="db.gpdusrhokctnctteocjw.supabase.co",
        database="postgres",
        user="postgres",
        password="937146",
        port="5432"
    )
    test_conn.close()
    
    # Se chegou até aqui, Supabase está disponível
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:937146@db.gpdusrhokctnctteocjw.supabase.co:5432/postgres"
    logger.info("Usando banco de dados Supabase (PostgreSQL)")
    
except Exception as e:
    # Fallback para SQLite se Supabase não estiver disponível
    logger.warning(f"Supabase não disponível ({e}), usando SQLite como fallback")
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.db')
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True
db = SQLAlchemy(app)

# --- Modelos do Banco de Dados ---
class Usuario(db.Model):
    __tablename__ = "Usuarios"
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_usuario = db.Column(db.String(80), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    nome_completo = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    perfil = db.Column(db.String(50), default="operador") # operador, supervisor
    data_criacao = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    conferencias = db.relationship("Conferencia", backref="responsavel", lazy=True)

    def __repr__(self):
        return f"<Usuario {self.nome_usuario}>"


class Conferencia(db.Model):
    __tablename__ = "Conferencias"
    id_conferencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario_responsavel = db.Column(db.Integer, db.ForeignKey("Usuarios.id_usuario"), nullable=False)
    numero_os = db.Column(db.String(100), nullable=False, index=True)
    nome_cliente_projeto = db.Column(db.String(200))
    nome_arquivo_original = db.Column(db.String(255))
    data_inicio_conferencia = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    data_fim_conferencia = db.Column(db.DateTime)
    observacoes_gerais = db.Column(db.Text)
    status_conferencia = db.Column(db.String(50), default="Em Andamento") # Em Andamento, Aprovado, Reprovado com Pendências
    itens_conferencia = db.relationship("ItemConferencia", backref="conferencia_pai", lazy=True, cascade="all, delete-orphan")
    processos_adicionais = db.relationship("ProcessoAdicionalConferencia", backref="conferencia_pai", lazy=True, uselist=False, cascade="all, delete-orphan")

class ItemConferencia(db.Model):
    __tablename__ = "ItensConferencia"
    id_item_conferencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_conferencia = db.Column(db.Integer, db.ForeignKey("Conferencias.id_conferencia"), nullable=False)
    codigo_item_checklist = db.Column(db.String(100), nullable=False)
    descricao_item_checklist = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.String(50)) # Conforme, Não Conforme, N/A
    observacao_item = db.Column(db.Text)

class ProcessoAdicionalConferencia(db.Model):
    __tablename__ = "ProcessosAdicionaisConferencia"
    id_processo_conferencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_conferencia = db.Column(db.Integer, db.ForeignKey("Conferencias.id_conferencia"), nullable=False)
    montou_boneca = db.Column(db.String(20))
    verificou_medida_faca = db.Column(db.String(20))
    enviou_cliche = db.Column(db.String(20))
    obs_enviou_cliche = db.Column(db.Text)
    enviou_fotolito = db.Column(db.String(20))
    obs_enviou_fotolito = db.Column(db.Text)
    deu_baixa_chapas = db.Column(db.String(20))
    fez_apontamento_sistema = db.Column(db.String(20))




class DefeitoComum(db.Model):
    __tablename__ = "DefeitosComuns"
    id_defeito = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)  # Crítico, Técnico, Qualidade, etc.
    descricao = db.Column(db.Text, nullable=False)
    causas = db.Column(db.Text, nullable=False)
    solucao = db.Column(db.Text, nullable=False)
    imagem_path = db.Column(db.String(255))
    data_criacao = db.Column(db.DateTime, default=datetime.datetime.utcnow)

CHECKLIST_ITEMS = [
    {"codigo": "TAMANHO_ARQUIVO", "descricao": "O TAMANHO DO ARQUIVO ESTÁ DE ACORDO?"},
    {"codigo": "MODO_COR_OS", "descricao": "O ARQUIVO ESTÁ NO MODO DE COR CONFORME SOLICITADO NA O.S?", "opcoes": ["PANTONE", "CMYK"]},
    {"codigo": "SANGRIA_5MM", "descricao": "O ARQUIVO POSSUI SANGRIA DE NO MÍNIMO 5MM?"},
    {"codigo": "PDF_X1A_2001", "descricao": "O ARQUIVO ESTÁ SALVO EM PDF X1-A/2001?"},
    {"codigo": "IMAGENS_300DPI_CMYK", "descricao": "VERIFIQUE SE TODAS AS IMAGENS ESTÃO COM NO MÍNIMO 300DPI\\\'S DE QUALIDADE E SE TODAS FORAM CONVERTIDAS PARA CMYK."},
    {"codigo": "SINALIZACAO_DESTAQUE", "descricao": "VERIFIQUE SE FOI FEITO SINALIZAÇÃO PARA O DESTAQUE."},
    {"codigo": "PRETO_TEXTOS_OBJETOS", "descricao": "VERIFIQUE A PORCENTAGEM DO PRETO NOS TEXTOS E DEMAIS OBJETOS (C=0, M=0, Y=0, K=100%)."},
    {"codigo": "ORTOGRAFIA_DIAGRAMACAO", "descricao": "VERIFIQUE A ORTOGRAFIA E A DIAGRAMAÇÃO DO DOCUMENTO."},
    {"codigo": "RESERVA_COLA", "descricao": "VERIFIQUE SE O ARQUIVO ESTÁ COM RESERVA DE COLA (se aplicável)."},
    {"codigo": "FACA_SOBREPOSTA_PANTONE", "descricao": "VERIFIQUE SE A FACA ESTÁ SOBREPOSTA E EM PANTONE (ou cor especial definida)."},
    {"codigo": "NOMENCLATURA_PDF", "descricao": "VERIFIQUE NOMENCLATURA NO PDF, COM NOME, NÚMERO O.S E QUANTIDADE DE IMPRESSÃO."},
    {"codigo": "SOLICITACAO_PRODUCAO", "descricao": "FOI FEITO A SOLICITAÇÃO DA PRODUÇÃO DA (FACA, CLICHÊ, FOTOLITO) SE HOUVER?"},
    {"codigo": "VERIFICOU_QRCODE", "descricao": "VERIFICOU O QRCODE?"},
    {"codigo": "FORMATO_COR_REFERENCIA", "descricao": "QUAL FORMATO DE COR SERÁ USADO PARA REFERÊNCIA?", "opcoes": ["EPSON", "MODELO_FISICO"]}
]

# Inicializar o banco de dados e criar usuário admin se não existir
def inicializar_banco_dados():
    with app.app_context():
        try:
            # Criar todas as tabelas
            db.create_all()
            
            # Verificar se já existe um usuário admin
            admin = Usuario.query.filter_by(nome_usuario='admin').first()
            if not admin:
                # Criar usuário admin padrão
                admin = Usuario(
                    nome_usuario='admin',
                    senha_hash=generate_password_hash('admin123'),
                    nome_completo='Administrador',
                    email='admin@example.com',
                    perfil='supervisor',
                    data_criacao=datetime.datetime.utcnow()
                )
                db.session.add(admin)
                
                # Criar usuário operador padrão
                operador = Usuario(
                    nome_usuario='operador',
                    senha_hash=generate_password_hash('operador123'),
                    nome_completo='Operador',
                    email='operador@example.com',
                    perfil='operador',
                    data_criacao=datetime.datetime.utcnow()
                )
                db.session.add(operador)
                
                db.session.commit()
                logger.info("Usuários padrão criados com sucesso!")
            
            # Inicializar biblioteca de defeitos
            if DefeitoComum.query.count() == 0:
                # Adicionar alguns defeitos comuns como exemplos
                defeitos = [
                    {
                        "titulo": "Sangria Insuficiente",
                        "categoria": "Crítico",
                        "descricao": "Arquivos com sangria menor que 5mm podem resultar em bordas brancas indesejadas após o corte.",
                        "causas": "Configuração incorreta do documento, desconhecimento das especificações de impressão, conversão inadequada entre formatos de arquivo.",
                        "solucao": "Solicitar ao cliente arquivo com sangria mínima de 5mm em todos os lados ou, se possível, estender elementos gráficos manualmente.",
                        "imagem_path": "images/sangria_insuficiente.jpg"
                    },
                    {
                        "titulo": "Trapping Incorreto",
                        "categoria": "Técnico",
                        "descricao": "Falhas no trapping podem causar espaços brancos ou sobreposições indesejadas entre cores adjacentes durante a impressão.",
                        "causas": "Configurações inadequadas de trapping, uso de cores especiais sem ajustes apropriados, diferenças de expansão entre tintas.",
                        "solucao": "Aplicar trapping adequado (geralmente 0.1 a 0.5pt) dependendo do tipo de impressão e substrato. Verificar áreas críticas onde cores contrastantes se encontram.",
                        "imagem_path": "images/trapping_incorreto.jpg"
                    },
                    {
                        "titulo": "Resolução Baixa de Imagens",
                        "categoria": "Qualidade",
                        "descricao": "Imagens com menos de 300 DPI podem aparecer pixeladas ou borradas na impressão final.",
                        "causas": "Uso de imagens da web (72 DPI), ampliação excessiva de imagens pequenas, compressão excessiva de JPEGs.",
                        "solucao": "Solicitar ao cliente imagens em alta resolução (mínimo 300 DPI no tamanho final). Em casos urgentes, utilizar software de upscaling com IA para melhorar a qualidade.",
                        "imagem_path": "images/resolucao_baixa.jpg"
                    }
                ]
                
                for defeito_data in defeitos:
                    defeito = DefeitoComum(**defeito_data)
                    db.session.add(defeito)
                
                db.session.commit()
                logger.info("Biblioteca de defeitos inicializada com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            db.session.rollback()

# Inicializar o banco de dados na inicialização do aplicativo
inicializar_banco_dados()

@app.template_filter("datetimeformat")
def datetimeformat(value, format="%d/%m/%Y %H:%M:%S"):
    if value is None:
        return ""
    return value.strftime(format)

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Implementação da pesquisa por número da O.S.
    pesquisa_os = request.args.get('pesquisa_os', '')
    
    # Se houver um termo de pesquisa, filtra as conferências
    if pesquisa_os:
        conferencias = Conferencia.query.filter(
            Conferencia.id_usuario_responsavel == session["user_id"],
            Conferencia.numero_os.like(f"%{pesquisa_os}%")
        ).order_by(Conferencia.data_fim_conferencia.desc()).all()
    else:
        # Caso contrário, mostra todas as conferências do usuário
        conferencias = Conferencia.query.filter_by(
            id_usuario_responsavel=session["user_id"]
        ).order_by(Conferencia.data_fim_conferencia.desc()).all()
    
    # Buscar o usuário atual para passar ao template
    usuario = Usuario.query.get(session["user_id"])
    
    return render_template("index.html", conferencias=conferencias, usuario=usuario)

@app.route("/login", methods=["GET", "POST"])
def login():
    # Garantir que o banco de dados esteja inicializado
    inicializar_banco_dados()
    
    if request.method == "POST":
        nome_usuario = request.form["nome_usuario"]
        senha = request.form["senha"]
        
        try:
            usuario = Usuario.query.filter_by(nome_usuario=nome_usuario).first()
            if usuario and check_password_hash(usuario.senha_hash, senha):
                session["user_id"] = usuario.id_usuario
                session["user_name"] = usuario.nome_usuario
                flash("Login bem-sucedido!", "success")
                return redirect(url_for("index"))
            else:
                flash("Nome de usuário ou senha inválidos.", "danger")
        except Exception as e:
            flash(f"Erro ao fazer login: {str(e)}", "danger")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    flash("Você foi desconectado.", "info")
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome_completo = request.form["nome_completo"]
        nome_usuario = request.form["nome_usuario"]
        senha = request.form["senha"]
        hashed_password = generate_password_hash(senha, method="pbkdf2:sha256")
        if Usuario.query.filter_by(nome_usuario=nome_usuario).first():
            flash("Nome de usuário já existe.", "danger")
            return render_template("register.html")
        novo_usuario = Usuario(nome_completo=nome_completo, nome_usuario=nome_usuario, senha_hash=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Usuário registrado com sucesso! Faça o login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/nova_conferencia", methods=["GET", "POST"])
def nova_conferencia():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    # Buscar o usuário atual para passar ao template
    usuario = Usuario.query.get(session["user_id"])
    
    if request.method == "POST":
        try:
            logger.info("Iniciando criação de nova conferência")
            numero_os = request.form["numero_os"]
            nome_cliente_projeto = request.form.get("nome_cliente_projeto")
            nome_arquivo_original = request.form.get("nome_arquivo_original")
            
            # Criar a conferência
            nova_conf = Conferencia(
                id_usuario_responsavel=session["user_id"],
                numero_os=numero_os,
                nome_cliente_projeto=nome_cliente_projeto,
                nome_arquivo_original=nome_arquivo_original
            )
            
            # Determinar o status final com base nas respostas
            status_final = "Aprovado"
            for item_base in CHECKLIST_ITEMS:
                codigo_item = item_base["codigo"]
                resposta_key = f"checklist__{codigo_item}"
                resposta = request.form.get(resposta_key)
                if resposta == "Não Conforme":
                    status_final = "Reprovado com Pendências"
                    break
            
            nova_conf.status_conferencia = status_final
            nova_conf.data_fim_conferencia = datetime.datetime.utcnow()
            
            # Adicionar a conferência ao banco de dados
            db.session.add(nova_conf)
            # Fazer flush para obter o ID
            db.session.flush()
            
            # Armazenar o ID em uma variável para garantir que seja preservado
            id_conferencia_gerado = nova_conf.id_conferencia
            logger.info(f"ID da conferência gerado: {id_conferencia_gerado}")
            
            # Adicionar os itens de checklist
            for item_base in CHECKLIST_ITEMS:
                codigo_item = item_base["codigo"]
                resposta_key = f"checklist__{codigo_item}"
                observacao_key = f"checklist_obs__{codigo_item}"
                resposta = request.form.get(resposta_key)
                observacao = request.form.get(observacao_key)
                item_conf = ItemConferencia(
                    id_conferencia=id_conferencia_gerado,
                    codigo_item_checklist=item_base["codigo"],
                    descricao_item_checklist=item_base["descricao"],
                    resposta=resposta,
                    observacao_item=observacao
                )
                db.session.add(item_conf)
            
            # Adicionar processos adicionais
            proc_add = ProcessoAdicionalConferencia(
                id_conferencia=id_conferencia_gerado,
                montou_boneca=request.form.get("montou_boneca"),
                verificou_medida_faca=request.form.get("verificou_medida_faca"),
                enviou_cliche=request.form.get("enviou_cliche"),
                obs_enviou_cliche=request.form.get("obs_enviou_cliche"),
                enviou_fotolito=request.form.get("enviou_fotolito"),
                obs_enviou_fotolito=request.form.get("obs_enviou_fotolito"),
                deu_baixa_chapas=request.form.get("deu_baixa_chapas"),
                fez_apontamento_sistema=request.form.get("fez_apontamento_sistema")
            )
            db.session.add(proc_add)
            
            # Adicionar observações gerais
            nova_conf.observacoes_gerais = request.form.get("observacoes_gerais")
            
            # Commit para salvar tudo no banco de dados
            db.session.commit()
            
            # Verificar se a conferência foi realmente salva
            conferencia_salva = Conferencia.query.get(id_conferencia_gerado)
            if conferencia_salva:
                logger.info(f"Conferência salva com sucesso. ID: {id_conferencia_gerado}")
                flash(f"Conferência para O.S. {numero_os} salva com sucesso! ID: {id_conferencia_gerado}", "success")
                # Garantir que estamos usando o ID armazenado para o redirecionamento
                return redirect(url_for("visualizar_conferencia", id_conferencia=id_conferencia_gerado))
            else:
                logger.error(f"Conferência não encontrada após commit. ID esperado: {id_conferencia_gerado}")
                flash("Erro: A conferência foi salva, mas não foi possível acessá-la. Por favor, verifique na lista de conferências.", "warning")
                return redirect(url_for("index"))
                
        except Exception as e:
            logger.error(f"Erro ao salvar conferência: {str(e)}")
            db.session.rollback()
            flash(f"Erro ao salvar conferência: {str(e)}", "danger")
            return redirect(url_for("index"))

    return render_template("nova_conferencia.html", checklist_items=CHECKLIST_ITEMS, usuario=usuario)

@app.route("/conferencia/<int:id_conferencia>")
def visualizar_conferencia(id_conferencia):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        # Buscar a conferência com tratamento de erro amigável
        logger.info(f"Buscando conferência com ID: {id_conferencia}")
        conferencia = Conferencia.query.get(id_conferencia)
        
        # Se a conferência não existir, exibir mensagem amigável
        if not conferencia:
            logger.warning(f"Conferência com ID {id_conferencia} não encontrada")
            flash(f"A conferência com ID {id_conferencia} não foi encontrada. Por favor, crie uma nova conferência ou selecione uma existente.", "warning")
            return redirect(url_for("index"))
        
        if conferencia.id_usuario_responsavel != session["user_id"]:
            logger.warning(f"Usuário {session['user_id']} tentou acessar conferência {id_conferencia} de outro usuário")
            flash("Você não tem permissão para ver esta conferência.", "danger")
            return redirect(url_for("index"))
        
        # Buscar o usuário atual para passar ao template
        usuario = Usuario.query.get(session["user_id"])
        
        logger.info(f"Conferência {id_conferencia} encontrada e exibida com sucesso")
        return render_template("conferencia_detalhe.html", conferencia=conferencia, usuario=usuario)
    except Exception as e:
        logger.error(f"Erro ao visualizar conferência {id_conferencia}: {str(e)}")
        flash(f"Erro ao visualizar conferência: {str(e)}", "danger")
        return redirect(url_for("index"))



@app.route("/conferencia/<int:id_conferencia>/pdf")
def gerar_pdf_conferencia(id_conferencia):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        # Buscar a conferência com tratamento de erro amigável
        conferencia = Conferencia.query.get(id_conferencia)
        
        # Se a conferência não existir, exibir mensagem amigável
        if not conferencia:
            flash(f"A conferência com ID {id_conferencia} não foi encontrada. Por favor, crie uma nova conferência ou selecione uma existente.", "warning")
            return redirect(url_for("index"))
        
        if conferencia.id_usuario_responsavel != session["user_id"]:
            flash("Você não tem permissão para gerar relatório desta conferência.", "danger")
            return redirect(url_for("index"))
        
        # Buscar o usuário atual para passar ao template
        usuario = Usuario.query.get(session["user_id"])
        
        # Renderizar template HTML para impressão
        return render_template("relatorio_conferencia_impressao.html", 
                            conferencia=conferencia, 
                            now=datetime.datetime.now(),
                            modo_impressao=True,
                            usuario=usuario)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF da conferência {id_conferencia}: {str(e)}")
        flash(f"Erro ao gerar relatório: {str(e)}", "danger")
        return redirect(url_for("index"))

# Nova rota para a biblioteca de defeitos
@app.route("/biblioteca_defeitos")
def biblioteca_defeitos():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Buscar o usuário atual para passar ao template
    usuario = Usuario.query.get(session["user_id"])
    
    # Aqui poderia buscar defeitos do banco de dados se implementado
    # defeitos = DefeitoComum.query.all()
    
    return render_template("biblioteca_defeitos.html", usuario=usuario)

# Rota para verificar o status do banco de dados
@app.route("/check_db")
def check_db():
    try:
        # Tentar inicializar o banco de dados
        inicializar_banco_dados()
        
        # Verificar se o usuário admin existe
        admin = Usuario.query.filter_by(nome_usuario='admin').first()
        if admin:
            return f"Banco de dados OK. Usuário admin encontrado (ID: {admin.id_usuario})."
        else:
            return "Banco de dados inicializado, mas usuário admin não encontrado."
    except Exception as e:
        return f"Erro ao verificar banco de dados: {str(e)}"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        inicializar_banco_dados()
    app.run(host="0.0.0.0", port=5000, debug=True)
