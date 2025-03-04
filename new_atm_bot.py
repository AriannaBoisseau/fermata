from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
import requests
from dotenv import load_dotenv
load_dotenv() 

TOKEN = os.getenv('TOKEN')
JSON_FILE = './preferiti.json'


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Cookie': '',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
}

def get_attesa(stop_number):
    url = f"https://giromilano.atm.it/proxy.tpportal/api/tpPortal/geodata/pois/stops/{stop_number}"
    response = requests.post(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        lines = data.get('Lines', [])
        ids = []
        wait_times = []
        for line in lines:
            ids.append(line.get('BookletUrl2', 'N/A'))
            wait_times.append(line.get('WaitMessage', 'N/A'))
    else:
        ids = [404]
        wait_times = ['Errore nel recupero del tempo di attesa']
    return ids, wait_times

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Benvenuto!\nUsa /impostazioni per modificare le fermate preferite\nUsa /attesa per visualizzare il tempo di attesa')

async def attesa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("1📍", callback_data='1'),
            InlineKeyboardButton("2📍", callback_data='2'),
            InlineKeyboardButton("3📍", callback_data='3'),
            InlineKeyboardButton("4📍", callback_data='4')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Per quale fermata desideri il tempo di attesa?', reply_markup=reply_markup)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Con questo menu puoi gestire le tue fermate preferite')

    keyboard = [
        [InlineKeyboardButton("Aggiungi fermata", callback_data='add')],
        [InlineKeyboardButton("Rimuovi fermata", callback_data='remove')],
        [InlineKeyboardButton("Visualizza fermate", callback_data='show')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Cosa vuoi fare:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'add':
        await query.message.reply_text('Per favore, inserisci il numero della fermata:')
        context.user_data['adding_stop'] = True
    elif query.data == 'remove':
        await query.message.reply_text('Per favore, inserisci il numero della fermata:')
        context.user_data['removing_stop'] = True
    elif query.data == 'show':
        user = query.from_user.username
        print(f"show from username: {user}")


        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        stops = user_stops.get(user, [])
        if stops:
            stops_text = '\n'.join([f"{index + 1}📍: {stop}" for index, stop in enumerate(stops)])
            await query.message.reply_text(f'Ecco le tue fermate preferite:\n{stops_text}')
        else:
            await query.message.reply_text('Non hai fermate preferite.')
    elif query.data in ['1', '2', '3', '4']:
        stop_index = int(query.data) - 1
        user = query.from_user.username

        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}
        
        if user not in user_stops:
            user_stops[user] = []
            await query.message.reply_text(f'Non hai fermate preferite.')
        else:
            if len(user_stops[user]) >= stop_index + 1:
                id, wait_time = get_attesa(user_stops[user][stop_index])
                text = ''
                for i in range(len(id)):
                    text += f'Attesa {id[i]}: {wait_time[i]}\n'
                await query.message.reply_text(text)
            else:
                await query.message.reply_text(f'Non hai impostato la {stop_index + 1}° fermata.\nUsa /impostazioni per aggiungere fermate ai preferiti.')

        keyboard = [
            [
                InlineKeyboardButton("1📍", callback_data='1'),
                InlineKeyboardButton("2📍", callback_data='2'),
                InlineKeyboardButton("3📍", callback_data='3'),
                InlineKeyboardButton("4📍", callback_data='4')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Per quale fermata desideri il tempo di attesa?', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('adding_stop'):
        stop_number = update.message.text
        user = update.message.from_user.username

        url = f"https://giromilano.atm.it/proxy.tpportal/api/tpPortal/geodata/pois/stops/{stop_number}"
        response = requests.post(url, headers=HEADERS)
        if response.status_code != 200:
            await update.message.reply_text(f'Il numero della fermata {stop_number} non è valido. Per favore, riprova.')
            context.user_data['adding_stop'] = False
            return

        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        if user not in user_stops:
            user_stops[user] = []
        if stop_number not in user_stops[user]:
            if len(user_stops[user]) == 4:
                await update.message.reply_text('Hai già 4 fermate preferite, per favore rimuovine una per aggiungerne un\'altra.')
                context.user_data['adding_stop'] = False
            else: 
                user_stops[user].append(stop_number)
                await update.message.reply_text(f'Fermata {stop_number} aggiunta con successo!')
                print(f"{user} added stop {stop_number}")
                context.user_data['adding_stop'] = False
        else:
            await update.message.reply_text(f'La fermata {stop_number} è già presente tra le tue fermate preferite.')
            context.user_data['adding_stop'] = False

        with open(JSON_FILE, 'w') as file:
            json.dump(user_stops, file, indent=4)

    elif context.user_data.get('removing_stop'):
        stop_number = update.message.text
        user = update.message.from_user.username

        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        if user not in user_stops:
            user_stops[user] = []
        if stop_number in user_stops[user]:
            user_stops[user].remove(stop_number)
            await update.message.reply_text(f'Fermata {stop_number} rimossa con successo!')
            print(f"{user} removed stop {stop_number}")
            context.user_data['removing_stop'] = False
        else:
            await update.message.reply_text(f'La fermata {stop_number} non è tra le tue fermate preferite.')
            context.user_data['removing_stop'] = False

        with open(JSON_FILE, 'w') as file:
            json.dump(user_stops, file, indent=4)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("impostazioni", settings))
    application.add_handler(CommandHandler("attesa", attesa))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
