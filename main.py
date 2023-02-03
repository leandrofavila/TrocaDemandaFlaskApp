from flask import Flask, render_template, request, redirect, session, flash, url_for
import cx_Oracle
import pandas as pd
import imaplib
from email.message import Message
from time import time


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
    ordens = ordem.split('\n')
    for j in ordens:
        jogo = Jogo(j, dem_out['num_ordem'][0] + ' - ' + dem_out['desc_tecnica'][0], dem_in + ' - ' + dem_out['desc_dem_in'][0])
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
    ordem = ordem.split()
    print(ordem)
    s = ','.join(ordem)
    print(s)
    cur.execute(
        r"SELECT TPL.COD_ITEM, TIT.DESC_TECNICA, (SELECT TIT.DESC_TECNICA FROM FOCCO3I.TITENS TIT WHERE TIT.COD_ITEM IN (" + request.form['dem_in'] + "))  "
        r"FROM FOCCO3I.TORDENS TOR "
        r"INNER JOIN FOCCO3I.TDEMANDAS TDE                    ON TOR.ID = TDE.ORDEM_ID "
        r"INNER JOIN FOCCO3I.TITENS_PLANEJAMENTO TPL          ON TDE.ITPL_ID = TPL.ID "
        r"INNER JOIN FOCCO3I.TITENS_EMPR EMP                  ON EMP.COD_ITEM = TPL.COD_ITEM "
        r"INNER JOIN FOCCO3I.TITENS TIT                       ON TIT.ID = EMP.ITEM_ID "
        r"WHERE TOR.NUM_ORDEM IN (" + s + ") "
    )
    dem_out_focco = cur.fetchall()
    dem_out_focco = pd.DataFrame(dem_out_focco, columns=['num_ordem', 'desc_tecnica', 'desc_dem_in'])
    return dem_out_focco


@app.route('/dispara_email', methods=['POST', ])
def dispara_email():
    connection = imaplib.IMAP4_SSL('10.40.3.12', 993)
    connection.login("ldeavila@sr.ind.br", "srengld21v3l1")
    new_message = Message()
    new_message["From"] = "leandrofavila@gmail.com"
    new_message["Subject"] = "Troca de demanda."
    new_message.set_payload(trata_email())
    connection.append('INBOX', '', imaplib.Time2Internaldate(time()), str(new_message).encode('utf-8'))
    flash('Ordens enviadas para supervisor da produção')
    lista.clear()
    return redirect(url_for('index'))


def trata_email():
    nlis = ''
    for x in lista:
        nlis = nlis + x.ordem + ' ' + x.dem_in + ' ' + x.dem_out + '\n'

    return nlis


if __name__ == '__main__':
    app.run(host='10.40.3.48', port=8010, debug=True)
