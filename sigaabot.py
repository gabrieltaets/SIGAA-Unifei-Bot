import logging
import os
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
import time

updater = Updater(token='')

dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
updater.start_polling()

def start(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="Olá, eu sou o SIGAA Bot!\nDigite /notas usuario senha e eu lhe enviarei suas notas!\nNão se preocupe - seus dados não são guardados!\nSe você gosta do SIGAA Bot, por favor deixe sua avaliação: https://telegram.me/storebot?start=SIGAA_Bot")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

def notas(bot, update, args):
	if(len(args) != 2):
		bot.send_message(chat_id=update.message.chat_id, text="Ops! A sintaxe deve ser /notas usuario senha")
		return
	USERLOGIN = args[0]
	USERPWD = args[1]
	if(len(USERLOGIN) != 11):
		bot.send_message(chat_id=update.message.chat_id, text="Ops! Parece que seu login não é válido! Lembre-se: seu login é o seu CPF!")
		return
	bot.send_message(chat_id=update.message.chat_id, text="Aguarde enquanto pego suas notas!")
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument("--incognito")
	chrome_options.add_argument("--headless")
	chrome_options.add_argument("--window-size=1000,1000")
	driver = webdriver.Chrome(chrome_options=chrome_options)
	try:
		driver.get("https://sigaa.unifei.edu.br/sigaa/verTelaLogin.do")
		login = driver.find_element_by_name("user.login")
		login.send_keys(USERLOGIN)
		pwd = driver.find_element_by_name("user.senha")
		pwd.send_keys(USERPWD)
		pwd.send_keys(Keys.ENTER)
		elem = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, ("ThemeOfficeMainItem"))))
		elem.click()
		notas = driver.find_element_by_class_name("ThemeOfficeMenuItemText")
		notas.click()
		driver.save_screenshot(""+USERLOGIN+".png")
		bot.send_photo(chat_id=update.message.chat_id, photo=open(""+USERLOGIN+".png","rb"), caption="Aqui estão suas notas!")
		os.remove(""+USERLOGIN+".png")
	except:
		bot.send_message(chat_id=update.message.chat_id, text="Sinto muito, não consegui recuperar suas notas!\nTalvez seus dados estejam incorretos, ou o SIGAA está fora do ar!")
	driver.quit()

notas_handler = CommandHandler('notas', notas, pass_args=True)
dispatcher.add_handler(notas_handler)