from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import json
import os
import requests
from dotenv import load_dotenv
load_dotenv() 

TOKEN = os.getenv('TOKEN')

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
        # Assuming the wait time is in the 'wait_time' field of the JSON response
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

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Benvenuto!\nUsa /impostazioni per modificare le fermate preferite\nUsa /attesa per visualizzare il tempo di attesa')

def attesa(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("1📍", callback_data='1'),
            InlineKeyboardButton("2📍", callback_data='2'),
            InlineKeyboardButton("3📍", callback_data='3'),
            InlineKeyboardButton("4📍", callback_data='4')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Per quale fermata desideri il tempo di attesa?', reply_markup=reply_markup)

def settings(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Con questo menu puoi gestire le tue fermate preferite')

    keyboard = [
        [InlineKeyboardButton("Aggiungi fermata", callback_data='add')],
        [InlineKeyboardButton("Rimuovi fermata", callback_data='remove')],
        [InlineKeyboardButton("Visualizza fermate", callback_data='show')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Cosa vuoi fare:', reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'add':
        query.message.reply_text('Per favore, inserisci il numero della fermata:')
        context.user_data['adding_stop'] = True
    elif query.data == 'remove':
        query.message.reply_text('Per favore, inserisci il numero della fermata:')
        context.user_data['removing_stop'] = True
    elif query.data == 'show':
        user = query.from_user.username
        print(f"show from username: {user}")

        # Path to the JSON file
        json_file_path = '/home/haribo/Documents/raspberry/preferiti.json'

        # Load existing data from the JSON file
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        # Get the user's stops
        stops = user_stops.get(user, [])
        if stops:
            stops_text = '\n'.join([f"{index + 1}📍: {stop}" for index, stop in enumerate(stops)])
            query.message.reply_text(f'Ecco le tue fermate preferite:\n{stops_text}')
        else:
            query.message.reply_text('Non hai fermate preferite.')
    elif query.data in ['1', '2', '3', '4']:
        stop_index = int(query.data) - 1
        user = query.from_user.username

        # Path to the JSON file
        json_file_path = '/home/haribo/Documents/raspberry/preferiti.json'

        # Load existing data from the JSON file
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}
        
        if user not in user_stops:
            user_stops[user] = []
            query.message.reply_text(f'Non hai fermate preferite.')
        else:
            if len(user_stops[user]) >= stop_index + 1:
                id, wait_time = get_attesa(user_stops[user][stop_index])
                text = ''
                for i in range(len(id)):
                    text += f'Attesa {id[i]}: {wait_time[i]}\n'
                query.message.reply_text(text)
            else:
                query.message.reply_text(f'Non hai impostato la {stop_index + 1}° fermata.\nUsa /impostazioni per aggiungere fermate ai preferiti.')

        keyboard = [
            [
                InlineKeyboardButton("1📍", callback_data='1'),
                InlineKeyboardButton("2📍", callback_data='2'),
                InlineKeyboardButton("3📍", callback_data='3'),
                InlineKeyboardButton("4📍", callback_data='4')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('Per quale fermata desideri il tempo di attesa?', reply_markup=reply_markup)


def handle_message(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('adding_stop'):
        stop_number = update.message.text
        user = update.message.from_user.username

        # Check if the stop number is valid by pinging the URL
        url = f"https://giromilano.atm.it/proxy.tpportal/api/tpPortal/geodata/pois/stops/{stop_number}"
        response = requests.post(url, headers=HEADERS)
        if response.status_code != 200:
            update.message.reply_text(f'Il numero della fermata {stop_number} non è valido. Per favore, riprova.')
            context.user_data['adding_stop'] = False
            return

        # Path to the JSON file
        json_file_path = '/home/haribo/Documents/raspberry/preferiti.json'

        # Load existing data from the JSON file
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        # Update the user's stops
        if user not in user_stops:
            user_stops[user] = []
        if stop_number not in user_stops[user]:
            if len(user_stops[user]) == 4:
                update.message.reply_text('Hai già 4 fermate preferite, per favore rimuovine una per aggiungerne un\'altra.')
                context.user_data['adding_stop'] = False
            else: 
                user_stops[user].append(stop_number)
                update.message.reply_text(f'Fermata {stop_number} aggiunta con successo!')
                print(f"{user} added stop {stop_number}")
                context.user_data['adding_stop'] = False
        else:
            update.message.reply_text(f'La fermata {stop_number} è già presente tra le tue fermate preferite.')
            context.user_data['adding_stop'] = False

        # Save the updated data back to the JSON file
        with open(json_file_path, 'w') as file:
            json.dump(user_stops, file, indent=4)

    elif context.user_data.get('removing_stop'):
        stop_number = update.message.text
        user = update.message.from_user.username

        # Path to the JSON file
        json_file_path = '/home/haribo/Documents/raspberry/preferiti.json'

        # Load existing data from the JSON file
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                user_stops = json.load(file)
        else:
            user_stops = {}

        # Update the user's stops
        if user not in user_stops:
            user_stops[user] = []
        if stop_number in user_stops[user]:
            user_stops[user].remove(stop_number)
            update.message.reply_text(f'Fermata {stop_number} rimossa con successo!')
            print(f"{user} removed stop {stop_number}")
            context.user_data['removing_stop'] = False
        else:
            update.message.reply_text(f'La fermata {stop_number} non è tra le tue fermate preferite.')
            context.user_data['removing_stop'] = False

        # Save the updated data back to the JSON file
        with open(json_file_path, 'w') as file:
            json.dump(user_stops, file, indent=4)

def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("impostazioni", settings))
    dispatcher.add_handler(CommandHandler("attesa", attesa))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

# TODO
# - migiorare rimozione fermate
# - print dimanico delle fermate preferite
# - personalizzazione print fermate preferite