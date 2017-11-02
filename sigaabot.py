import logging
import os
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext.dispatcher import run_async
import telegram
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
from pyvirtualdisplay import Display
from PIL import Image
import time
import mysql.connector
import sys
import threading
import ujson

display = Display(visible=0, size=(1280,2560))
display.start()

updater = Updater(token=TOKEN)

dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def error_callback(bot, update, error):
    try:
        raise error
    except Exception as inst:
    	print(type(inst))
    	print(inst.args)
    	print(inst)
dispatcher.add_error_handler(error_callback)

@run_async
def start(bot, update):
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	user = bot.get_chat(update.message.chat_id)
	kbs = [["Sim", "Não"]]
	query = "INSERT INTO sigaabot(chat_id, login, password, name, state) VALUES(%s,null,null,%s, 'start1') ON DUPLICATE KEY UPDATE name = %s, state = 'start1'"
	cursor.execute(query,(str(update.message.chat_id), user.first_name, user.first_name) );
	cursor.close()
	conn.commit();
	conn.close();
	log(chat_id=update.message.chat_id, request='/start', comments='Sucesso')
	bot.send_message(chat_id=update.message.chat_id, text="Olá "+user.first_name+", eu sou o SIGAA Bot, criado por Gabriel Taets!\nVamos me configurar conforme suas preferências.")
	rkm = telegram.ReplyKeyboardMarkup(keyboard=kbs, resize_keyboard=False, one_time_keyboard=True)
	resp = bot.send_message(chat_id=update.message.chat_id, text="Você quer que eu guarde seu usuário e senha do SIGAA?", reply_markup=rkm);

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

def checkDatabase(bot, update):
	try:
		conn = mysql.connector.connect(**config)
	except Exception as e:
		print(type(e))
		print(e.args)
		print(e)
		return;
	cursor = conn.cursor(buffered=True)
	query = "select chat_id from sigaabot where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	if cursor.rowcount < 1:	
		bot.send_message(update.message.chat_id, "O SIGAA Bot foi atualizado e precisa ser reconfigurado! Digite /start para configurá-lo.")
		cursor.close()
		conn.close()
		return False
	cursor.fetchall()
	cursor.close()
	conn.close()
	return True

def log(log_id=None, chat_id=ADM_ID, request='', comments=''):
	try:
		try:
			conn = mysql.connector.connect(**config)
		except:
			return;
		cursor = conn.cursor()
		if log_id == None:
			query = "insert into log(chat_id, request, bot_token, comments) values(%s, %s, %s, %s)"
			cursor.execute(query,(str(chat_id), request, TOKEN, comments))
			log_id = cursor.lastrowid
		else:
			query = "update log set comments=%s where log_id=%s"
			cursor.execute(query,(comments, str(log_id)))
		conn.commit()
		cursor.close()
		conn.close()
	except:
		return None
	return log_id

@run_async
def notas(bot, update, args):
	if checkDatabase(bot, update) == False:
		return
	log_id = log(chat_id=update.message.chat_id, request="/notas ")
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	query = "select flag, login, CAST(AES_DECRYPT(password,'"+AES_KEY+"') AS CHAR(100)) from sigaabot where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	usuario = cursor.fetchone()
	cursor.close()
	conn.close()
	if usuario[0] == 0 and len(args) != 2:
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser: /notas <usuario> <senha>")
		log(log_id=log_id, comments='Falha: Erro de Sintaxe')
		return
	if usuario[0] == 0:
		USERLOGIN = args[0]
		USERPWD = args[1]
	else:
		USERLOGIN = usuario[1]
		USERPWD = usuario[2]
	if(len(USERLOGIN) != 11):
		bot.send_message(chat_id=update.message.chat_id, text="Ops! Parece que seu login não é válido! Lembre-se: seu login é o seu CPF!")
		log(log_id=log_od, comments='Falha: Login inválido')
		return
	bot.send_message(chat_id=update.message.chat_id, text="Aguarde enquanto pego suas notas!")
	options = webdriver.ChromeOptions()
	options.add_argument('--no-sandbox')
	driver = webdriver.Chrome(chrome_options=options)
	try:
		driver.implicitly_wait(10)
		driver.get("https://sigaa.unifei.edu.br/sigaa/verTelaLogin.do")
		login = driver.find_element_by_name("user.login")
		login.send_keys(USERLOGIN)
		pwd = driver.find_element_by_name("user.senha")
		pwd.send_keys(USERPWD)
		pwd.send_keys(Keys.ENTER)

		if(driver.current_url == 'https://sigaa.unifei.edu.br/sigaa/telaAvisoLogon.jsf'):
			try:
				elem = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, ("j_id_jsp_75580718_1:j_id_jsp_75580718_2"))))
				elem.click()
			except Exception as e:
				print(type(e))
				print(e.args)
				print(e)
				pass
		try:
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.CLASS_NAME, ("ThemeOfficeMainItem"))))
			elem.click()
		except:
			raise Exception('auterr')
		notas = driver.find_element_by_class_name("ThemeOfficeMenuItemText")
		notas.click()
		driver.save_screenshot("notas/"+USERLOGIN+".png")
		elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, ("relatorio-paisagem-container"))))
		loc1 = elem.location
		sz1 = elem.size
		elem2 = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.XPATH,("//table[@class='tabelaRelatorio']"))))
		loc2 = elem2.location
		sz2 = elem2.size
		im = Image.open("notas/"+USERLOGIN+".png")
		im = im.crop((loc1['x'],loc1['y'],loc1['x']+sz1['width'],loc1['y']+loc2['y']+sz2['height']))
		im.save("notas/"+USERLOGIN+".png")
		bot.send_photo(chat_id=update.message.chat_id, photo=open("notas/"+USERLOGIN+".png","rb"), caption="Aqui estão suas notas!")
		log(log_id=log_id, comments='Sucesso')
	except Exception as e:
		if e.args[0] == 'auterr':
			bot.send_message(chat_id=update.message.chat_id, text="Login ou senha incorretos!")
			log(log_id=log_id, comments='Falha: Login ou Senha incorretos')
		else:
			bot.send_message(chat_id=update.message.chat_id, text="Sinto muito, não consegui recuperar suas notas!\nTalvez seus dados estejam incorretos, ou o SIGAA está fora do ar!\nSe o erro persistir, por favor mande um /feedback!")
			log(log_id=log_id, comments='Falha: '+str(e))
	driver.quit()

notas_handler = CommandHandler('notas', notas, pass_args=True)
dispatcher.add_handler(notas_handler)

@run_async
def disc(bot, update, args):
	if checkDatabase(bot, update) == False:
		return
	log_id = log(chat_id=update.message.chat_id, request='/disc')
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	query = "select flag, login, CAST(AES_DECRYPT(password,'"+AES_KEY+"') AS CHAR(100)) from sigaabot where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	usuario = cursor.fetchone()
	cursor.close()
	conn.close()
	if usuario[0] == 0 and len(args) != 3:
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser: /disc <sigla> <usuario> <senha>")
		log(log_id=log_id, comments='Falha: Erro de Sintaxe')
		return
	elif usuario[0] == 1 and len(args) != 1:
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser: /disc <sigla>")
		log(log_id=log_id, comments='Falha: Erro de Sintaxe')
		return
	DISC = args[0].upper()
	if usuario[0] == 0:
		USERLOGIN = args[1]
		USERPWD = args[2]
	else:
		USERLOGIN = usuario[1]
		USERPWD = usuario[2]
	if(len(USERLOGIN) != 11):
		bot.send_message(chat_id=update.message.chat_id, text="Ops! Parece que seu login não é válido! Lembre-se: seu login é o seu CPF!")
		log(log_id=log_id, comments=''+DISC+': Falha: Login inválido')
		return
	bot.send_message(chat_id=update.message.chat_id, text="Aguarde enquanto pego suas notas!")
	options = webdriver.ChromeOptions()
	options.add_argument('--no-sandbox')
	driver = webdriver.Chrome(chrome_options=options)
	try:
		driver.get("https://sigaa.unifei.edu.br/sigaa/verTelaLogin.do")
		login = driver.find_element_by_name("user.login")
		login.send_keys(USERLOGIN)
		pwd = driver.find_element_by_name("user.senha")
		pwd.send_keys(USERPWD)
		pwd.send_keys(Keys.ENTER)
		if(driver.current_url == 'https://sigaa.unifei.edu.br/sigaa/telaAvisoLogon.jsf'):
			try:
				elem = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, ("j_id_jsp_75580718_1:j_id_jsp_75580718_2"))))
				elem.click()
			except Exception as e:
				print(type(e))
				print(e.args)
				print(e)
				pass
		try:
			elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, ("sair-sistema"))))
		except:
			raise Exception('auterr')
		try:
			elem = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, ("//div[@id='turmas-portal']//td[@class='descricao']//a[1]"))))
			elem.click()
		except:
			raise Exception('unknown')
		elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, ("formAcoesTurma:botaoTrocarTurma"))))
		elem.click()
		try:
			elem = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, (""+DISC))))
			elem.click()
		except:
			bot.send_message(chat_id=update.message.chat_id, text="Não consegui encontrar essa disciplina!");
			log(log_id=log_id, comments=''+DISC+': Falha: Disciplina não encontrada')
		else:
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.CLASS_NAME, ("itemMenuHeaderAlunos"))))
			elem.click()
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.LINK_TEXT, ("Ver Notas"))))
			elem.click()
			try:
				elem = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.LINK_TEXT, ("Voltar"))))
			except:
				bot.send_message(chat_id=update.message.chat_id, text="As notas dessa disciplina ainda não foram lançadas!")
				log(log_id=log_id, comments=''+DISC+': Falha: Disciplina sem notas')
			else:
				driver.save_screenshot("disc/"+USERLOGIN+DISC+".png")
				elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, ("relatorio-paisagem-container"))))
				loc = elem.location
				sz = elem.size
				im = Image.open("disc/"+USERLOGIN+DISC+".png")
				im = im.crop((loc['x'],loc['y'],loc['x']+sz['width'],loc['y']+sz['height']))
				im.save("disc/"+USERLOGIN+DISC+".png")
				bot.send_photo(chat_id=update.message.chat_id, photo=open("disc/"+USERLOGIN+DISC+".png","rb"), caption="Aqui estão suas notas de "+DISC+"!")
				log(log_id=log_id, comments=''+DISC+': Sucesso')
	except Exception as e:
		if e.args[0] == 'unknown':
			bot.send_message(chat_id=update.message.chat_id, text="Desculpe, tive um erro! Tente novamente mais tarde.\nSe o erro persistir, por favor mande um /feedback!")
			log(log_id=log_id, comments=''+DISC+': Falha: Erro desconhecido '+str(e))
		elif e.args[0] == 'auterr':
			bot.send_message(chat_id=update.message.chat_id, text="Login ou senha incorretos!")
			log(log_id=log_id, comments=''+DISC+': Falha: Login ou Senha incorretos')
		else:
			bot.send_message(chat_id=update.message.chat_id, text="Sinto muito, não consegui recuperar suas notas!\nTalvez seus dados estejam incorretos, ou o SIGAA está fora do ar!\nSe o erro persistir, por favor mande um /feedback!")
			log(log_id=log_id, comments=''+DISC+': Falha: '+str(e))
	driver.quit()

disc_handler = CommandHandler('disc', disc, pass_args=True)
dispatcher.add_handler(disc_handler)

@run_async
def freq(bot, update, args):
	if checkDatabase(bot, update) == False:
		return
	log_id = log(chat_id=update.message.chat_id, request='/freq')
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	query = "select flag, login, CAST(AES_DECRYPT(password,'"+AES_KEY+"') AS CHAR(100)) from sigaabot where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	usuario = cursor.fetchone()
	cursor.close()
	conn.close()
	if usuario[0] == 0 and len(args) != 3:
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser: /freq <sigla> <usuario> <senha>")
		log(log_id=log_id, comments='Falha: Erro de Sintaxe')
		return
	elif usuario[0] == 1 and len(args) != 1:
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser: /freq <sigla>")
		log(log_id=log_id, comments='Falha: Erro de Sintaxe')
		return
	DISC = args[0].upper()
	if usuario[0] == 0:
		USERLOGIN = args[1]
		USERPWD = args[2]
	else:
		USERLOGIN = usuario[1]
		USERPWD = usuario[2]
	if(len(USERLOGIN) != 11):
		bot.send_message(chat_id=update.message.chat_id, text="Ops! Parece que seu login não é válido! Lembre-se: seu login é o seu CPF!")
		log(log_id=log_id, comments=''+DISC+' Falha: Login inválido')
		return
	bot.send_message(chat_id=update.message.chat_id, text="Aguarde enquanto pego sua frequência!")
	options = webdriver.ChromeOptions()
	options.add_argument('--no-sandbox')
	driver = webdriver.Chrome(chrome_options=options)
	try:
		driver.get("https://sigaa.unifei.edu.br/sigaa/verTelaLogin.do")
		login = driver.find_element_by_name("user.login")
		login.send_keys(USERLOGIN)
		pwd = driver.find_element_by_name("user.senha")
		pwd.send_keys(USERPWD)
		pwd.send_keys(Keys.ENTER)
		if(driver.current_url == 'https://sigaa.unifei.edu.br/sigaa/telaAvisoLogon.jsf'):
			try:
				elem = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, ("j_id_jsp_75580718_1:j_id_jsp_75580718_2"))))
				elem.click()
			except Exception as e:
				print(type(e))
				print(e.args)
				print(e)
				pass
		try:
			elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, ("sair-sistema"))))
		except:
			raise Exception('auterr')
		try:
			elem = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, ("//div[@id='turmas-portal']//td[@class='descricao']//a[1]"))))
			elem.click()
		except:
			raise Exception('unknown')
		elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, ("formAcoesTurma:botaoTrocarTurma"))))
		elem.click()
		try:
			elem = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, (""+DISC))))
			elem.click()
		except:
			bot.send_message(chat_id=update.message.chat_id, text="Não consegui encontrar essa disciplina!");
			log(log_id=log_id, comments=''+DISC+': Falha: Disciplina não encontrada')
		else:
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.CLASS_NAME, ("itemMenuHeaderAlunos"))))
			elem.click()
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.LINK_TEXT, ("Frequência"))))
			elem.click()
			driver.save_screenshot("freq/"+USERLOGIN+DISC+".png")
			elem = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, ("scroll-wrapper"))))
			loc = elem.location
			sz = elem.size
			im = Image.open("freq/"+USERLOGIN+DISC+".png")
			im = im.crop((loc['x'],loc['y'],loc['x']+sz['width'],loc['y']+sz['height']))
			im.save("freq/"+USERLOGIN+DISC+".png")
			bot.send_photo(chat_id=update.message.chat_id, photo=open("freq/"+USERLOGIN+DISC+".png","rb"), caption="Aqui está sua frequência de "+DISC+"!")
			log(log_id=log_id, comments=''+DISC+': Sucesso')
	except Exception as e:
		if e.args[0] == 'unknown':
			bot.send_message(chat_id=update.message.chat_id, text="Desculpe, tive um erro! Tente novamente mais tarde.\nSe o erro persistir, por favor mande um /feedback!")
			log(log_id=log_id, comments=''+DISC+': Falha: Erro desconhecido '+str(e))
		elif e.args[0] == 'auterr':
			bot.send_message(chat_id=update.message.chat_id, text="Login ou senha incorretos!")
			log(log_id=log_id, comments=''+DISC+': Falha: Login ou Senha incorretos')
		else:
			bot.send_message(chat_id=update.message.chat_id, text="Sinto muito, não consegui recuperar sua frequência!\nTalvez seus dados estejam incorretos, ou o SIGAA está fora do ar!\nSe o erro persistir, por favor mande um /feedback!")
			log(log_id=log_id, comments=''+DISC+': Falha: '+str(e))
	driver.quit()

freq_handler = CommandHandler('freq', freq, pass_args=True)
dispatcher.add_handler(freq_handler)

@run_async
def help(bot, update):
	if checkDatabase(bot, update) == False:
		return
	log_id = log(chat_id=update.message.chat_id, request='/help')
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	query = "select flag from sigaabot where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	flag = cursor.fetchone()
	cursor.close()
	conn.close()
	try:
		if flag[0] == 0:
			bot.send_message(chat_id=update.message.chat_id, text="\nVou te ajudar a ver suas notas do SIGAA Unifei!\nComandos:\n/start - configura o SIGAA Unifei Bot\n/help - exibe os comandos\n/notas <usuario> <senha> - Obter as notas de todas as disciplinas\n/disc <sigla> <usuario> <senha> - Obter as notas da disciplina indicada\n/freq <sigla> <usuario> <senha> - Obter a frequencia para a disciplina indicada\n/feedback <mensagem> -- envia uma mensagem para meu criador\n\nSe você gosta do SIGAA Bot, por favor deixe sua avaliação: https://telegram.me/storebot?start=SIGAA_Bot")
		else:
			bot.send_message(chat_id=update.message.chat_id, text="\nVou te ajudar a ver suas notas do SIGAA Unifei!\nComandos:\n/start - configura o SIGAA Unifei Bot\n/help - exibe os comandos\n/notas - Obter as notas de todas as disciplinas\n/disc <sigla> - Obter as notas da disciplina indicada\n/freq <sigla> - Obter a frequência para a disciplina indicada\n/feedback <mensagem> -- envia uma mensagem para meu criador\n\nSe você gosta do SIGAA Bot, por favor deixe sua avaliação: https://telegram.me/storebot?start=SIGAA_Bot")
		log(log_id=log_id, comments='Sucesso')
	except Exception as e:
		log(log_id=log_id, comments='Falha: '+str(e))

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

def getData(bot, update, step, text=None):
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	if step == "start1":
		query = "update sigaabot set state = 'start2' where chat_id = " + str(update.message.chat_id)
		cursor.execute(query)
		bot.send_message(chat_id=update.message.chat_id, text="Ótimo! Me diga seu CPF.")
	if step == "start2":
		if len(text) == 11 and text.isdigit():
			query = "update sigaabot set state = 'start3', login = '" + text + "' where chat_id = " + str(update.message.chat_id)
			cursor.execute(query)
			bot.send_message(chat_id=update.message.chat_id, text="Agora me diga sua senha.")
		else:
			bot.send_message(chat_id=update.message.chat_id, text="Ops! Seu CPF não é válido.")
	if step == "start3":
		if "\"" not in text and "'" not in text and ";" not in text:
			query = "update sigaabot set state = '', flag = 1, password = AES_ENCRYPT('" + text + "','"+AES_KEY+"') where chat_id = " + str(update.message.chat_id)
			cursor.execute(query)
			bot.send_message(chat_id=update.message.chat_id, text="Prontinho! Agora você não precisa mais me dizer seu login e senha nos comandos!")
		else:
			query = "update sigaabot set state = '', flag = 0, login = '' where chat_id = " + str(update.message.chat_id)
			cursor.execute(query)
			bot.send_message(chat_id=update.message.chat_id, text="Desculpe, por motivos de segurança não consigo salvar senhas que contenham esses caracteres!")
		help(bot, update)
	cursor.close()
	conn.commit()
	conn.close()

def removeData(bot, update):
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	query = "update sigaabot set flag = 0, login = null, password = null, state = '' where chat_id = " + str(update.message.chat_id)
	cursor.execute(query)
	cursor.close()
	conn.commit()
	conn.close()
	bot.send_message(chat_id=update.message.chat_id, text="Prontinho! Não salvarei suas informações.")

@run_async
def feedback(bot, update, args):
	if checkDatabase(bot, update) == False:
		return
	if len(args) < 1:
		log(chat_id=update.message.chat_id, request='/feedback', comments='Falha: argumento faltando')
		bot.send_message(chat_id=update.message.chat_id, text='Uso: /feedback <mensagem>')
		return
	user = bot.get_chat(update.message.chat_id)
	if user.username == None:
		user.username = ''
	if user.first_name == None:
		user.first_name = ''
	if user.last_name == None:
		user.last_name = ''
	try:
		bot.send_message(chat_id=update.message.chat_id, text="Obrigado pelo feedback!")
		bot.send_message(chat_id=ADM_ID, text="Feedback:\nchat_id: "+str(update.message.chat_id)+"\nNome: "+user.first_name+" "+user.last_name+"\nUsername: "+user.username+"\nMensagem: "+' '.join(args))
		log(chat_id=update.message.chat_id, request='/feedback '+' '.join(args), comments='Sucesso')
	except Exception as e:
		log(chat_id=update.message.chat_id, request='/feedback '+' '.join(args), comments='Falha: '+str(e))

feedback_handler = CommandHandler('feedback', feedback, pass_args=True)
dispatcher.add_handler(feedback_handler)

@run_async
def answer(bot, update):
	if checkDatabase(bot, update) == False:
		return
	query = "select state from sigaabot where chat_id = " + str(update.message.chat_id)
	try:
		conn = mysql.connector.connect(**config)
	except:
		return;
	cursor = conn.cursor()
	cursor.execute(query)
	state = cursor.fetchone()
	cursor.close()
	conn.close()
	opt = update.message.text
	if state[0] == "":
		return
	if state[0] == "start1":
		if opt == "Sim":
			getData(bot, update, state[0], opt)
		elif opt == "Não":
			removeData(bot, update)
	if state[0] == "start2":
		getData(bot, update, state[0], opt)
	if state[0] == "start3":
		getData(bot, update, state[0], opt)

answer_handler = MessageHandler(Filters.text, answer)
dispatcher.add_handler(answer_handler)
