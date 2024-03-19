from flask import Flask, render_template, request, redirect, session, flash, url_for
import cx_Oracle
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import pyodbc
import re


class Troca_dem:
    def __init__(self, ordem, cod_item, desc_item, dem_out, dem_in):
        self.ordem = ordem
        self.cod_item = cod_item
        self.desc_item = desc_item
        self.dem_out = dem_out
        self.dem_in = dem_in


class Usuario:
    def __init__(self, nome, nickname, senha):
        self.nome = nome
        self.nickname = nickname
        self.senha = senha


lista_email = []
lista = []

usuario1 = Usuario('KBCA', 'kbca', 'alo')
usuario2 = Usuario('pana', 'pana', '123')
usuario3 = Usuario('barriga', 'barriga', '123')
usuario4 = Usuario('amanda', 'amanda', 'qualidade01')
usuario5 = Usuario('luciano', 'luciano', 'qualidade02')

usuarios = {usuario1.nickname: usuario1,
            usuario2.nickname: usuario2,
            usuario3.nickname: usuario3,
            usuario4.nickname: usuario4,
            usuario5.nickname: usuario5
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
    for j in dem_out.iterrows():
        jogo = Troca_dem(j[1][0], j[1][1], j[1][2], j[1][3] + ' - ' + j[1][4], dem_in + ' - ' + j[1][6])
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
            flash(usuario.nickname + ' logado com Sucesso!')
            proxima_pagina = request.form['proxima']
            return redirect(proxima_pagina)
    else:
        flash('Usuario não logado')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session['usuario_logado'] = None
    flash('Logout Efetuado')
    lista.clear()
    return redirect(url_for('index'))


def focco(ordem):
    dsn = cx_Oracle.makedsn("10.40.3.10", 1521, service_name="f3ipro")
    connection = cx_Oracle.connect(user=r"focco_consulta", password=r'consulta3i08', dsn=dsn, encoding="UTF-8")
    cur = connection.cursor()
    ordem = ordem.split()
    s = ','.join(ordem)
    cur.execute(
        r"SELECT DISTINCT TOR.NUM_ORDEM, TIT2.COD_ITEM, TIT2.DESC_TECNICA, TPL.COD_ITEM, TIT.DESC_TECNICA "
        r"FROM FOCCO3I.TORDENS TOR "
        r"INNER JOIN FOCCO3I.TDEMANDAS TDE                    ON TOR.ID = TDE.ORDEM_ID "
        r"INNER JOIN FOCCO3I.TITENS_PLANEJAMENTO TPL          ON TDE.ITPL_ID = TPL.ID "
        r"INNER JOIN FOCCO3I.TITENS_EMPR EMP                  ON EMP.COD_ITEM = TPL.COD_ITEM "
        r"INNER JOIN FOCCO3I.TITENS TIT                       ON TIT.ID = EMP.ITEM_ID "
        r"INNER JOIN FOCCO3I.TITENS_PLANEJAMENTO TPL2         ON TOR.ITPL_ID = TPL2.ID "
        r"INNER JOIN FOCCO3I.TITENS_EMPR EMP2                 ON EMP2.COD_ITEM = TPL2.COD_ITEM "
        r"INNER JOIN FOCCO3I.TITENS TIT2                      ON TIT2.ID = EMP2.ITEM_ID "
        r"WHERE TOR.NUM_ORDEM IN (" + s + ") "
        r"AND TIT.DESC_TECNICA NOT LIKE '%TINTA%' "
    )
    dem_out_focco = cur.fetchall()
    connection.commit()
    cur.execute(
        r"SELECT TIT.COD_ITEM, TIT.DESC_TECNICA "
        r"FROM FOCCO3I.TITENS TIT "
        r"WHERE TIT.COD_ITEM IN (" + request.form['dem_in'] + ") "
    )
    dem_out_focco_dem_in = cur.fetchall()
    dem_out_focco_dem_in = pd.DataFrame(dem_out_focco_dem_in, columns=['dem_in', 'desc_dem_in'])
    dem_out_focco = pd.DataFrame(dem_out_focco, columns=['num_ordem',
                                                         'cod_item',
                                                         'desc_ordem',
                                                         'num_dem',
                                                         'desc_tecnica'
                                                         ])

    dem_out_focco['dem_in'] = dem_out_focco_dem_in['dem_in'][0]
    dem_out_focco['desc_dem_in'] = dem_out_focco_dem_in['desc_dem_in'][0]
    return dem_out_focco


@app.route('/dispara_email', methods=['POST', ])
def dispara_email():
    add_bd()
    msg = MIMEMultipart()
    message = trata_email()
    password = "srengld21v3l1"
    msg['From'] = "ldeavila@sr.ind.br"
    recipients = ["ldeavila@sr.ind.br", "producao@sr.ind.br", "qualidade@sr.ind.br", "luciano@sr.ind.br"]  # "producao@sr.ind.br", "wesley@sr.ind.br"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = "Troca de Demanda"
    msg.attach(MIMEText(message, 'plain'))
    server = smtplib.SMTP('10.40.3.12: 465')
    server.starttls()
    try:
        server.login(msg['From'], password)
    except IndentationError as err:
        print(f'Senha fora alterada - {err}')


    server.sendmail(msg['From'], recipients, msg.as_string())
    server.quit()
    flash('Ordens enviadas para o(a) supervisor(a) avaliar')
    lista.clear()
    return redirect(url_for('index'))


def trata_email():
    df = pd.DataFrame([vars(d) for d in lista])
    df_uniq = df['dem_in'].unique()
    nlis = sauda() + '\nFavor trocar a(s) demanda(s) da(s) orden(s) relacionada(s) abaixo:\n \n'
    for x in df_uniq:
        condi = df.loc[df['dem_in'] == x, 'dem_out'].iloc[0]
        nlis += 'Sai a demanda: ' + condi + '\n' \
                + 'Entra a demanda: ' + x + '\n \n'
        for idx, vals in df.iterrows():
            if vals['dem_in'] == x:
                nlis += '\t' + '•' + str(vals['ordem']) + ' - ' + str(vals['cod_item']) + ' - ' + str(
                    vals['desc_item']) + '\n'
        nlis += '\n ___________________________________________________________________________________\n \n'
    nlis += '\n \nQualquer duvida estou a disposição.\nAtt.'
    return nlis


def sauda():
    currentTime = datetime.datetime.now()
    if currentTime.hour < 12:
        return 'Bom dia: '
    elif 12 <= currentTime.hour <= 18:
        return 'Boa tarde: '
    else:
        return 'Boa noite: '


def add_bd():
    df = pd.DataFrame([vars(d) for d in lista])
    conn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                          "Server=ALFA\SQLEXPRESS;"
                          "Database=ReaData;"
                          "UID=PCPUser;"
                          "PWD=*$rUserPcP;")
    cursor = conn.cursor()
    for item in df.index:
        #print(df['cod_item'][item])
        dem_out = re.findall('([^\s]+)', df['dem_out'][item])
        dem_in = re.findall('([^\s]+)', df['dem_in'][item])
        cursor.execute(r"insert into [ReaData].[dbo].[tTrocaDem]"
                       r"(ORDEM, DEM_OUT, DEM_IN, DT_IN) "
                       r"values(" + str(df['ordem'][item]) + ", " + str(dem_out[0]) + ", " + str(dem_in[0]) + ", getdate()) ")
        conn.commit()


if __name__ == '__main__':
    app.run(host='10.40.3.48', port=8010, debug=True)
