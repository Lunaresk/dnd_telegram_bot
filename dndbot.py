from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (CommandHandler, MessageHandler, RegexHandler, ConversationHandler, CallbackQueryHandler, Filters)
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
import helpFuncs
import dbFuncs
from bottoken import getToken
import logging

updater = getToken()
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

SETNAME = range(1)

dbFuncs.initDB()

#TODO Check if lobby is present
# args should be the code of a lobby
def start(bot, update, args, user_data):
  dbFuncs.initCurrent(update.message.from_user['id'])
  checkUserData(update.message.from_user['id'], user_data)
  if len(args) == 0:
    bot.send_message(chat_id=update.message.chat_id, text="Hey buddy! Welcome to the DnD Messenger bot. It allows your character to talk/whisper to other characters without anyone else except the Dungeon Master reading it.\nIf you are a DM, please type /new\nOtherwise, ask your DM for the correct code\link to join a group.")
    return ConversationHandler.END
  if len(args[0]) != 10:
    bot.send_message(chat_id = update.message.chat_id, text = "The length of the code is strange. It should be 10 characters long. Please try again.")
    return ConversationHandler.END
  if dbFuncs.isAvailable(args[0]):
    user_data['lobby'] = args[0]
    if update.message.from_user['id'] == dbFuncs.getDM(user_data['lobby']):
      user_data['character'] = "DM"
    else:
      user_data['character'] = dbFuncs.getOwnCharacter(update.message.from_user['id'], user_data['lobby'])
    if user_data['character'] != None:
      bot.send_message(chat_id = update.message.chat_id, text = "Changed the Dungeon. You are now playing as {0}".format(user_data['character']))
      initMessage(bot, update, user_data)
      return ConversationHandler.END
    dmchat = dbFuncs.getDM(user_data['lobby'])
    dmname = bot.getChat(chat_id = dmchat).first_name
    title = dbFuncs.getLobbyTitle(user_data['lobby'])
    bot.send_message(chat_id = update.message.chat_id, text = u"Cool! You're joining {0} from {1}. Send now the name of your Character, so that the others can identify you.".format(title, dmname))
    return SETNAME
  bot.send_message(chat_id = update.message.chat_id, text = "I wasn't able to find the lobby. Please ask your DM for the code again.")
  return ConversationHandler.END

def new(bot, update, args, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  if len(args) != 0:
    title = helpFuncs.correctArgs(args)
    code = ""
    dm = update.message.from_user['id']
    dmchat = update.message.chat_id
    for i in range(10):
      code = helpFuncs.id_generator()
      if dbFuncs.isAvailable(code):
        break
    user_data['lobby'] = code
    user_data['character'] = ""
    dbFuncs.insertGame(code, title, dm)
    bot.send_message(chat_id = dmchat, text = "Gratulation! Game created. Use this code to invite your group to your game:")
    bot.send_message(chat_id = dmchat, text = u"[Join {0}](https://telegram.me/DnDPPbot?start={1}".format(title, code), parse_mode = 'Markdown')
    return initMessage(bot, update, user_data)
  else:
    bot.send_message(chat_id = update.message.chat_id, text = "Great! Please enter a Title for your round.")
    return SETNAME

def gameName(bot, update, user_data):
  return new(bot, update, update.message.text, user_data)

def playerName(bot, update, user_data):
  user_data['character'] = update.message.text
  player = update.message.from_user['id']
  character = user_data['character']
  code = user_data['lobby']
  dbFuncs.insertPlayers(player, character, code)
  bot.send_message(chat_id = update.message.chat_id, text = "Nice work! Now you can communicate with your party and DM.")
  return initMessage(bot, update, user_data)

#TODO Finish change lobby
def changeLobby(bot, update, user_data):
  if len(update.message.text) >= 11:
    code = update.message.text[1:11]
  checkUserData(update.message.from_user['id'], user_data)
  if not dbFuncs.isAvailable(code):
    bot.send_message(chat_id = update.message.chat_id, text = "I wasn't able to find the lobby. Please check your code for typos and check for case sensitive.")
    return ConversationHandler.END
  test = dbFuncs.getDM(code)
  if test == update.message.from_user['id']:
    user_data['character'] = ""
    user_data['lobby'] = code
    return initMessage(bot, update, user_data)
  temp = dbFuncs.getOwnCharacter(update.message.from_user['id'], code)
  if temp != None:
    user_data['character'] = temp
    user_data['lobby'] = code
    return initMessage(bot, update, user_data)
  return start(bot, update, code, user_data)

#TODO finish cancel
def cancel(bot, update):
  bot.send_message(chat_id = update.message.chat_id, text = "Action cancelled. What else can I do for you?")
  return ConversationHandler.END

def roll(bot, update, args, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  theText = ""
  if len(args) == 0:
    theText = helpFuncs.diceParser(["1d20"])
  else:
    theText = helpFuncs.diceParser(''.join(args).split("+"))
  sendText(bot, theText, user_data, 'r')

#TODO edit old message to more than just Deprecated
def initMessage(bot, update, user_data):
  message = update.message
  oldMessage = dbFuncs.getCurrentMessage(update.message.from_user['id'])
  if oldMessage != None:
    bot.edit_message_text(chat_id = message.chat_id, message_id = oldMessage, text = "Deprecated")
  user_data['sendTo'] = []
  keyboard = createKeyboard(message, user_data)
  title = dbFuncs.getLobbyTitle(user_data['lobby'])
  dmchat = dbFuncs.getDM(user_data['lobby'])
  dmname = bot.getChat(chat_id = dmchat).first_name
  saveMessage = bot.send_message(chat_id = message.chat_id, text = u"{0} /{1}\nDungeonMaster: {2}".format(title, user_data['lobby'], dmname), reply_markup = InlineKeyboardMarkup(keyboard)).message_id
  dbFuncs.updateMessageInCurrent(message.from_user['id'], saveMessage)
  dbFuncs.updateGameInCurrent(message.from_user['id'], user_data['lobby'])
  return ConversationHandler.END

def editMessage(bot, update, user_data):
  query = update.callback_query
  message = query.message
  currentMessage = dbFuncs.getCurrentMessage(query.from_user['id'])
  if message.message_id != currentMessage:
    bot.edit_message_text(chat_id = message.chat_id, message_id = message.message_id, text = u"{0}\n(Deprecated)".format(message.text))
    return
  checkUserData(query.from_user['id'], user_data)
  player = query.data
  if player != "refresh":
    if player in user_data['sendTo']:
      user_data['sendTo'].remove(player)
    else:
      user_data['sendTo'].append(player)
  keyboard = createKeyboard(query, user_data)
  try:
    bot.edit_message_reply_markup(chat_id = message.chat_id, message_id = message.message_id, reply_markup = InlineKeyboardMarkup(keyboard))
    bot.answer_callback_query(callback_query_id = query.id)
  except BadRequest:
    bot.answer_callback_query(callback_query_id = query.id, text = "Nobody else joined")

def createKeyboard(message, user_data):
  keyboard = [[InlineKeyboardButton("🔄 Refresh 🔄", callback_data = "refresh")]]
  pcharas = dbFuncs.getPlayerCharas(user_data['lobby'])
  pchats = dbFuncs.getPlayers(user_data['lobby'])
  if pchats != None and pcharas != None:
    if message.from_user['id'] in pchats and user_data['character'] in pcharas:
      pchats.remove(message.from_user['id'])
      pcharas.remove(user_data['character'])
    for i in range(len(pchats)):
      if str(pchats[i]) in user_data['sendTo']:
        keyboard.append([InlineKeyboardButton("✔ " + pcharas[i], callback_data = pchats[i])])
      else:
        keyboard.append([InlineKeyboardButton("❌ " + pcharas[i], callback_data = pchats[i])])
  return keyboard

def checkUserData(id, user_data):
  if 'id' not in user_data:
    user_data['id'] = id
  if 'lobby' not in user_data:
    user_data['lobby'] = dbFuncs.getCurrentLobby(id)
  if 'character' not in user_data:
    user_data['character'] = dbFuncs.getOwnCharacter(id, user_data['lobby'])
  if 'sendTo' not in user_data:
    user_data['sendTo'] = []
  

def handleText(bot, update, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  sendText(bot, update.message.text, user_data, 'm')

#TODO make it more beautiful...
def sendText(bot, theText, user_data, action):
  code = user_data['lobby']
  if code == None:
    return
  dmchat = dbFuncs.getDM(code)
  pchats = dbFuncs.getPlayers(code)
  pcharas = dbFuncs.getPlayerCharas(code)
  own = user_data['character']
  chats = []
  charas = []
  for i in range(len(pchats)):
    if str(pchats[i]) in user_data['sendTo']:
      chats.append(pchats[i])
      charas.append(pcharas[i])
  charlist = ", ".join(charas)
  if dmchat == user_data['id']:
    if len(user_data['sendTo']) == 0:
      if action == 'm':
        chats = pchats
      elif action == 'r':
        chats = dmchat
    for i in chats:
      bot.send_message(chat_id = i, text = u"{0}".format(theText))
  elif len(chats) == 0:
    if action == 'm':
      bot.send_message(chat_id = dmchat, text = u"{0}:\n{1}".format(own, theText))
    elif action == 'r':
      bot.send_message(chat_id = dmchat, text = u"{0} {1}".format(own, theText))
      bot.send_message(chat_id = user_data['id'], text = theText)
  else:
    bot.send_message(chat_id = dmchat, text = u"{0} to {1}:\n{2}".format(own, charlist, theText))
    for i in chats:
      if i == update.message.from_user['id']:
        if action == 'r':
          bot.send_message(chat_id = user_data['id'], text = theText)
        continue
      if action == 'm':
        bot.send_message(chat_id = i, text = u"{0}:\n{1}".format(own, theText))
      elif action == 'r':
        bot.send_message(chat_id = i, text = u"{0} {1}".format(own, theText))

def help(bot, update, args):
  if len(args) == 0:
    bot.send_message(chat_id = update.message.chat_id, text = "I appreciate your support and for using me. Here is a brief tutorial:\nWhen you're a DM (DungeonMaster), you can create a new lobby by typing /new [Title of the game] and I will give you a message you can forward to your people and wait for them to join. Press the Refresh button when you think someone new joined (will be improved soon).\n\nIf you are a player and just got invited to a game, you should first send me your character's name when I ask you to. After that, you get a message from me with buttons.\nWhen there's a red cross next to a character, it means, messages you are sending will not be sent to them.\nWhen there's a checkmark next to a character, it means that these characters are going to receive your message.\nWhen none of the characters are checked, you're just chatting with the DM. When you are the DM and none are checked, you're talking to everyone.\n\nAlways remember that your DM has to know everything and therefore gets every message you're sending to anyone.\n\nWhen you need help on a specific topic, type '/help [keypword]' (eg '/help roll') to get help with it.\n\nWhen you got errors or suggestions, please send them to my creator @Lunaresk. Have Fun!")
  elif args[0] == 'roll':
    bot.send_message(chat_id = update.message.chat_id, text = "You want to roll some dice? Great! Just type '/roll' and then text in this form '3d20' where the number behind the d stands for the die and the number before the d stands for the number of corresponding dice you want to roll.\nFor example: '/roll 2d10' would roll two ten-sided dice for you.\n\nYou can also combine different dice with that form: '/roll 2d6 + 4d8'\nThis way, you would roll (for example) two six-sided dice and four eight-sided dice.\n\nIf the d is missing (eg. '/roll d6 + 10') I'll treat it as a modifier. This input would result in one six-sided die added to 10.\n\nImportant: you can't throw more than 20 dice at once. Have fun!")
  else:
    bot.send_message(chat_id = update.message.chat_id, text = "I don't understand. Here's a list of currently available keywords:\nroll\n\nIf you want some general help, just type /help.")

def error_callback(bot, update, error):
  try:
    raise error
  except Unauthorized:
    print ('UnauthorizedError >> ' + str(error))
    # remove update.message.chat_id from conversation list
  except BadRequest:
    print ('BadRequestError >> ' + str(error))
    # handle malformed requests - read more below!
  except TimedOut:
    print ('TimedOutError >> ' + str(error))
    # handle slow connection problems
  except NetworkError:
    print ('NetworkError >> ' + str(error))
    # handle other connection problems
  except ChatMigrated as e:
    print ('ChatMigratedError >> ' + str(error))
    # the chat_id of a group has changed, use e.new_chat_id instead
  except TelegramError:
    print ('AnotherError >> ' + str(error))
    # handle all other telegram related errors

newGame = ConversationHandler(
  entry_points = [CommandHandler('new', new, pass_args = True, pass_user_data = True)],
  states = {
    SETNAME: [MessageHandler(Filters.text, gameName, pass_user_data = True)]
  },
  fallbacks = [CommandHandler('cancel', cancel)]
)

joinGame = ConversationHandler(
  entry_points = [CommandHandler('start', start, pass_args = True, pass_user_data = True), RegexHandler('^\/[0-9A-Za-z]{10}$', changeLobby, pass_user_data = True)],
  states = {
    SETNAME: [MessageHandler(Filters.text, playerName, pass_user_data = True)]
  },
  fallbacks = [CommandHandler('cancel', cancel)]
)

dispatcher.add_handler(joinGame)
dispatcher.add_handler(newGame)
dispatcher.add_handler(CommandHandler('help', help, pass_args = True))
dispatcher.add_handler(CommandHandler('roll', roll, pass_args = True, pass_user_data = True))
dispatcher.add_handler(CallbackQueryHandler(editMessage, pass_user_data = True))
dispatcher.add_handler(MessageHandler(Filters.text, handleText, pass_user_data = True))
dispatcher.add_error_handler(error_callback)
updater.start_polling()

updater.idle()

dbFuncs.close()
