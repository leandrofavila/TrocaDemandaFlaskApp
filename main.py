from flask import Flask, render_template, request, redirect, session, flash, url_for
import cx_Oracle


class Jogo:
    def __init__(self, ordem, dem_out, dem_in):
        self.ordem = ordem
        self.dem_out = dem_out
        self.dem_in = dem_in


class Usuario:
    def __init__(self, nome, nickname, senha):
        self.nome = nome
        self.nickname = nickname
        self.senha = senha


lista = []

usuario1 = Usuario('KBCA', 'kbca', 'alo')
usuario2 = Usuario('pana', 'pana', '123')
usuario3 = Usuario('pançudo', 'barriga', '123')

usuarios = {usuario1.nickname: usuario1,
            usuario2.nickname: usuario2,
            usuario3.nickname: usuario3
            }

app = Flask(__name__)

app.secret_key = 'kbca'
                   



@app.route('/')
def index():
    if 'usuario_logado' not in session or session['usuario_logado'] is None:
        return redirect(url_for('login', proxima=url_for('index')))
    return render_template('lista.html', titulo='Ordens', jogos=lista)


@app.route('/criar', methods=['POST', ])
def criar():
    ordem = request.form['ordem']
    dem_in = request.form['dem_in']
    dem_out = focco(ordem)
    jogo = Jogo(ordem, dem_out, dem_in)
    lista.append(jogo)
    return redirect(url_for('index'))


@app.route('/login')
def login():
    proxima = request.args.get('proxima')
    return render_template('login.html', proxima=proxima)


@app.route('/autenticar', methods=['POST', ])
def autenticar():
    if request.form['usuario'] in usuarios:
        usuario = usuarios[request.form['usuario']]
        if request.form['senha'] == usuario.senha:
            session['usuario_logado'] = usuario.nickname
            flash(usuario.nickname + ' Logado com Sucesso!')
            proxima_pagina = request.form['proxima']
            return redirect(proxima_pagina)
    else:
        flash('Usuario não logado')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session['usuario_logado'] = None
    flash('Logout Efetuado')
    return redirect(url_for('index'))


def focco(ordem):
    dsn = cx_Oracle.makedsn("10.40.3.10", 1521, service_name="f3ipro")
    connection = cx_Oracle.connect(user=r"focco_consulta", password=r'consulta3i08', dsn=dsn, encoding="UTF-8")
    cur = connection.cursor()
    cur.execute(
        r"SELECT TPL.COD_ITEM  "
        r"FROM FOCCO3I.TORDENS TOR "
        r"INNER JOIN FOCCO3I.TDEMANDAS TDE                    ON TOR.ID = TDE.ORDEM_ID "
        r"INNER JOIN FOCCO3I.TITENS_PLANEJAMENTO TPL          ON TDE.ITPL_ID = TPL.ID "
        r"WHERE TOR.NUM_ORDEM IN (" + ordem + ") "
    )
    dem_out_focco = cur.fetchall()
    print(type(dem_out_focco))
    return dem_out_focco


@app.route('/dispara_email', methods=['POST', ])
def dispara_email():
    print('pana_dev')
    lista.clear()
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(host='10.40.3.48', port=8010, debug=True)


