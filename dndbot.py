from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (CommandHandler, MessageHandler, RegexHandler, ConversationHandler, CallbackQueryHandler, Filters)
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
import helpFuncs
import bottoken
import logging

updater = bottoken.getToken()
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

SETNAME = range(1)

helpFuncs.initDB()

#TODO Check if lobby is present
# args should be the code of a lobby
def start(bot, update, args, user_data):
  helpFuncs.initCurrent(update.message.from_user['id'])
  checkUserData(update.message.from_user['id'], user_data)
  if len(args) == 0:
    bot.send_message(chat_id=update.message.chat_id, text="Hey buddy! Welcome to the DnD Messenger bot. It allows your character to talk/whisper to other characters without anyone else except the Dungeon Master reading it.\nIf you are a DM, please type /new\nOtherwise, ask your DM for the correct code\link to join a group.")
    return ConversationHandler.END
  if len(args[0]) != 10:
    bot.send_message(chat_id = update.message.chat_id, text = "The length of the code is strange. It should be 10 characters long. Please try again.")
    return ConversationHandler.END
  if helpFuncs.isAvailable(args[0]):
    user_data['lobby'] = args[0]
    if update.message.from_user['id'] == helpFuncs.getDM(user_data['lobby']):
      user_data['character'] = "DM"
    else:
      user_data['character'] = helpFuncs.getOwnCharacter(update.message.from_user['id'], user_data['lobby'])
    if user_data['character'] != None:
      bot.send_message(chat_id = update.message.chat_id, text = "Changed the Dungeon. You are now playing as {0}".format(user_data['character']))
      initMessage(bot, update, user_data)
      return ConversationHandler.END
    bot.send_message(chat_id = update.message.chat_id, text = "Cool! Send now the name of your Character, so that the others can identify you.")
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
      if helpFuncs.isAvailable(code):
        break
    user_data['lobby'] = code
    user_data['character'] = ""
    helpFuncs.insertGame(code, title, dm)
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
  helpFuncs.insertPlayers(player, character, code)
  bot.send_message(chat_id = update.message.chat_id, text = "Nice work! Now you can communicate with your party and DM.")
  return initMessage(bot, update, user_data)

#TODO Finish change lobby
def changeLobby(bot, update, user_data):
  if len(update.message.text) >= 11:
    code = update.message.text[1:11]
  checkUserData(update.message.from_user['id'], user_data)
  if not helpFuncs.isAvailable(code):
    bot.send_message(chat_id = update.message.chat_id, text = "I wasn't able to find the lobby. Please check your code for typos and check for case sensitive.")
    return ConversationHandler.END
  test = helpFuncs.getDM(code)
  if test == update.message.from_user['id']:
    user_data['character'] = ""
    user_data['lobby'] = code
    return initMessage(bot, update, user_data)
  temp = helpFuncs.getOwnCharacter(update.message.from_user['id'], code)
  if temp != None:
    user_data['character'] = temp
    uder_data['lobby'] = code
    return ConversationHandler.END
  return start(bot, update, code, user_data)

#TODO finish cancel
def cancel(bot, update):
  bot.send_message(chat_id = update.message.chat_id, text = "Action cancelled. What else can I do for you?")
  return ConversationHandler.END


#TODO edit old message to more than just Deprecated
def initMessage(bot, update, user_data):
  message = update.message
  oldMessage = helpFuncs.getCurrentMessage(update.message.from_user['id'])
  if oldMessage != None:
    bot.edit_message_text(chat_id = message.chat_id, message_id = oldMessage, text = "Deprecated")
  user_data['sendTo'] = []
  keyboard = createKeyboard(message, user_data)
  title = helpFuncs.getLobbyTitle(user_data['lobby'])
  dmchat = helpFuncs.getDM(user_data['lobby'])
  dmname = bot.getChat(chat_id = dmchat).first_name
  saveMessage = bot.send_message(chat_id = message.chat_id, text = u"{0} /{1}\nDungeonMaster: {2}".format(title, user_data['lobby'], dmname), reply_markup = InlineKeyboardMarkup(keyboard)).message_id
  helpFuncs.updateMessageInCurrent(message.from_user['id'], saveMessage)
  helpFuncs.updateGameInCurrent(message.from_user['id'], user_data['lobby'])
  return ConversationHandler.END

def editMessage(bot, update, user_data):
  query = update.callback_query
  message = query.message
  currentMessage = helpFuncs.getCurrentMessage(query.from_user['id'])
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
  pcharas = helpFuncs.getPlayerCharas(user_data['lobby'])
  pchats = helpFuncs.getPlayers(user_data['lobby'])
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
  if 'lobby' not in user_data:
    user_data['lobby'] = helpFuncs.getCurrentLobby(id)
  if 'character' not in user_data:
    user_data['character'] = helpFuncs.getOwnCharacter(id, user_data['lobby'])
  if 'sendTo' not in user_data:
    user_data['sendTo'] = []


#TODO
def handleText(bot, update, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  code = user_data['lobby']
  if code == None:
    return
  dmchat = helpFuncs.getDM(code)
  pchats = helpFuncs.getPlayers(code)
  pcharas = helpFuncs.getPlayerCharas(code)
  own = user_data['character']
  chats = []
  charas = []
  for i in range(len(pchats)):
    if str(pchats[i]) in user_data['sendTo']:
      chats.append(pchats[i])
      charas.append(pcharas[i])
  charlist = ", ".join(charas)
  if dmchat == update.message.chat_id:
    if len(user_data['sendTo']) == 0:
      chats = helpFuncs.getPlayers(code)
    for i in chats:
      bot.send_message(chat_id = i, text = u"{0}".format(update.message.text))
  elif len(chats) == 0:
    bot.send_message(chat_id = dmchat, text = u"{0}:\n{1}".format(own, update.message.text))
  else:
    bot.send_message(chat_id = dmchat, text = u"{0} to {1}:\n{2}".format(own, charlist, update.message.text))
    for i in chats:
      if i == update.message.from_user['id']:
        continue
      bot.send_message(chat_id = i, text = u"{0}:\n{1}".format(own, update.message.text))

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
dispatcher.add_handler(CallbackQueryHandler(editMessage, pass_user_data = True))
dispatcher.add_handler(MessageHandler(Filters.text, handleText, pass_user_data = True))
dispatcher.add_error_handler(error_callback)
updater.start_polling()

updater.idle()

helpFuncs.close()
