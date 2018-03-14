from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (CommandHandler, MessageHandler, RegexHandler, ConversationHandler, CallbackQueryHandler, Filters)
from ..errorCallback import error_callback
from . import helpFuncs
from . import dbFuncs
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# SETNAME used for the conversationhandlers
SETNAME = range(1)


# args should be the code of a lobby
def start(bot, update, args, user_data):
  dbFuncs.initCurrent(update.message.from_user['id'])
  checkUserData(update.message.from_user['id'], user_data)
  if len(args) == 0:
    bot.send_message(chat_id=update.message.chat_id, text="Hey buddy! Welcome to the DnD Messenger bot. It allows your character to talk/whisper to other characters without anyone else except the Dungeon Master reading it.\nIf you are a DM, please type /new\nOtherwise, ask your DM for the correct code\link to join a group.")
    return ConversationHandler.END
  args = ''.join(args)
  if checkCode(args, update.message.from_user['id']):
    bot.send_message(chat_id = update.message.chat_id, text = checkCode(args)+" Please ask your DM for help.")
    return ConversationHandler.END
  user_data['lobby'] = args
  if update.message.from_user['id'] == dbFuncs.getDM(args):
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

def new(bot, update, args, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  if len(args) != 0:
    title = helpFuncs.correctArgs(args)
    code = ""
    dm = update.message.from_user['id']
    for i in range(10):
      code = helpFuncs.id_generator()
      if not dbFuncs.isAvailable(code):
        break
    if dbFuncs.isAvailable(code):
      bot.send_message(chat_id = dm, text = "I wasn't able to create a lobby. I'm sorry, please try again.")
      return ConversationHandler.END
    user_data['lobby'] = code
    user_data['character'] = ""
    dbFuncs.insertGame(code, title, dm)
    bot.send_message(chat_id = dm, text = "Gratulation! Game created. Use this code to invite your group to your game:")
    bot.send_message(chat_id = dm, text = u"[Join {0}](https://telegram.me/DnDPPbot?start={1}".format(title, code), parse_mode = 'Markdown')
    return initMessage(bot, update, user_data)
  else:
    bot.send_message(chat_id = update.message.chat_id, text = "Great! Please enter a Title for your round.")
    return SETNAME

def my(bot, update):
  games = dbFuncs.getGames(update.message.from_user['id'])
  if len(games) == 0:
    bot.send_message(chat_id = update.message.chat_id, text = "There is currently no lobby you're in. Get a group together and change this.")
    return
  theText = "Here's a list of games you're currently in (I recommend not to join more than two games):\n"
  for i in games:
    theText += "\n" + dbFuncs.getLobbyTitle(i) + " /" + i
  bot.send_message(chat_id = update.message.chat_id, text = theText)

def close(bot, update, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  if user_data['id'] == dbFuncs.getDM(user_data['lobby']):
    dbFuncs.closeLobby(user_data['lobby'])
    bot.send_message(chat_id = update.message.chat_id, text = "Lobby closed. Nobody can join now.")
    return
  bot.send_message(chat_id = update.message.chat_id, text = "You are not the DM of this lobby. You can't close or open it.")

def open(bot, update, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  if user_data['id'] == dbFuncs.getDM(user_data['lobby']):
    dbFuncs.openLobby(user_data['lobby'])
    bot.send_message(chat_id = update.message.chat_id, text = "Lobby opened. Others can join now.")
    return
  bot.send_message(chat_id = update.message.chat_id, text = "You are not the DM of this lobby. You can't close or open it.")

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

def changeLobby(bot, update, user_data):
  return start(bot, update, update.message.text[1:], user_data)

def regexSlash(bot, update):
  bot.send_message(chat_id = update.message.chat_id, text = checkCode(update.message.text[1:]))

def checkCode(code, id = -1):
  if len(code) != 10:
    return "Your code hasn't got the right length. It should be 10 characters long."
  elif not dbFuncs.isAvailable(code):
    return "The code you sent me doesn't belong to any lobby."
  elif not dbFuncs.isOpen(code):
    if id in dbFuncs.getPlayers(code) or id == dbFuncs.getDM(code):
      return False
    return "The lobby you're trying to join is currently closed."
  return False

def leave(bot, update, user_data):
  checkUserData(update.message.from_user['id'], user_data)
  if user_data['lobby'] == None:
    bot.send_message(chat_id = update.message.chat_id, text = "You are currently not actively in a lobby you can leave. Please enter a lobby again and then use this command.")
    return ConversationHandler.END
  title = dbFuncs.getLobbyTitle(user_data['lobby'])
  if dbFuncs.getDM(user_data['lobby']) == user_data['id']:
    bot.send_message(chat_id = update.message.chat_id, text = u"You are the DM of this round. when you leave, the whole lobby will be deleted.")
  bot.send_message(chat_id = update.message.chat_id, text = u"You won't be able to send messages to your teammates nor will you receive their's. Are you really sure you want to leave {0}? If so, send 'I am sure'.".format(title))
  return SETNAME

def leaveLobby(bot, update, user_data):
  if update.message.text.lower() != 'i am sure':
    bot.send_message(chat_id = user_data['id'], text = "I don't understand. If you want to cancel, just type '/cancel'.")
    return SETNAME
  players = dbFuncs.getPlayers(user_data['lobby'])
  title = dbFuncs.getLobbyTitle(user_data['lobby'])
  if dbFuncs.getDM(user_data['lobby']) == user_data['id']:
    dbFuncs.removeGame(user_data['lobby'])
    for i in players:
      bot.send_message(chat_id = i, text = u"Your DM removed the game {0}. You're on your own now.".format(title))
  else:
    players.append(dbFuncs.getDM(user_data['lobby']))
    players.remove(user_data['id'])
    character = user_data['character']
    dbFuncs.removePlayerFromGame(user_data['id'], user_data['lobby'])
    for i in players:
      bot.send_message(chat_id = i, text = u"{0} left the game. Please refresh your lobby.".format(character))
  user_data.clear()
  checkUserData(update.message.from_user['id'], user_data)
  bot.send_message(chat_id = user_data['id'], text = "You left the game.")
  return ConversationHandler.END

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
  dbFuncs.updateSendtoInCurrent(user_data['id'], user_data['sendTo'])
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
    player = int(player)
    if player in user_data['sendTo']:
      user_data['sendTo'].remove(player)
    else:
      user_data['sendTo'].append(player)
    dbFuncs.updateSendtoInCurrent(user_data['id'], user_data['sendTo'])
  keyboard = createKeyboard(query, user_data)
  try:
    bot.edit_message_reply_markup(chat_id = message.chat_id, message_id = message.message_id, reply_markup = InlineKeyboardMarkup(keyboard))
    bot.answer_callback_query(callback_query_id = query.id)
  except:
    bot.answer_callback_query(callback_query_id = query.id, text = "Nobody else joined")

def createKeyboard(message, user_data):
  keyboard = [[InlineKeyboardButton("🔄 Refresh 🔄", callback_data = "refresh")]]
  pcharas = dbFuncs.getPlayerCharas(user_data['lobby'])
  pchats = dbFuncs.getPlayers(user_data['lobby'])
  if message.from_user['id'] in pchats and user_data['character'] in pcharas:
    pchats.remove(message.from_user['id'])
    pcharas.remove(user_data['character'])
  for i in range(len(pchats)):
    if pchats[i] in user_data['sendTo']:
      keyboard.append([InlineKeyboardButton("✔ " + pcharas[i], callback_data = pchats[i])])
    else:
      keyboard.append([InlineKeyboardButton("❌ " + pcharas[i], callback_data = pchats[i])])
  return keyboard

def checkUserData(id, user_data):
  user_data['id'] = id
  user_data['lobby'] = dbFuncs.getCurrentLobby(id)
  user_data['character'] = dbFuncs.getOwnCharacter(id, user_data['lobby'])
  if 'sendTo' not in user_data:
    user_data['sendTo'] = dbFuncs.getCurrentSendto(id)
  else:
    test = dbFuncs.getPlayers(user_data['lobby'])
    for i in user_data['sendTo']:
      if i not in test:
        user_data['sendTo'].remove(i)
    dbFuncs.updateSendtoInCurrent(id, user_data['sendTo'])

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
  if len(pchats) == 0:
    bot.send_message(chat_id = user_data['id'], text = "Nobody is in here. Invite some people.")
  pcharas = dbFuncs.getPlayerCharas(code)
  own = user_data['character']
  chats = []
  charas = []
  for i in range(len(pchats)):
    if pchats[i] in user_data['sendTo']:
      chats.append(pchats[i])
      charas.append(pcharas[i])
  charlist = ", ".join(charas)
  if action == 'm':
    if dmchat == user_data['id']:
      if len(user_data['sendTo']) == 0:
        chats += pchats
      for i in chats:
        bot.send_message(chat_id = i, text = theText)
    elif len(chats) == 0:
      bot.send_message(chat_id = dmchat, text = u"{0}:\n{1}".format(own, theText))
    else:
      bot.send_message(chat_id = dmchat, text = u"{0} to {1}:\n{2}".format(own, charlist, theText))
      for i in chats:
        bot.send_message(chat_id = i, text = u"{0}:\n{1}".format(own, theText))
  elif action == 'r':
    if dmchat == user_data['id']:
      bot.send_message(chat_id = user_data['id'], text = theText)
      for i in chats:
        bot.send_message(chat_id = i, text = u"DM {0}".format(theText))
    elif len(chats) == 0:
      bot.send_message(chat_id = dmchat, text = u"{0} {1}".format(own, theText))
      bot.send_message(chat_id = user_data['id'], text = theText)
    else:
      bot.send_message(chat_id = dmchat, text = u"{0} to {1}:\n{2}".format(own, charlist, theText))
      bot.send_message(chat_id = user_data['id'], text = theText)
      for i in chats:
        bot.send_message(chat_id = i, text = u"{0} {1}".format(own, theText))
  bot.send_chat_action(chat_id = user_data['id'], action = "typing")

def help(bot, update, args):
  if len(args) == 0:
    bot.send_message(chat_id = update.message.chat_id, text = "I appreciate your support and for using me. When you need help on a specific topic, type '/help [keyword]' (eg '/help roll') to get help with it.\nCurrently supported commands for help are: DM, new, Player, join, roll\n\nWhen you got errors or suggestions, please send them to my creator @Lunaresk. For the sourcecode, please check https://github.com/Lunaresk/dnd_telegram_bot.\nHave Fun!")
    return
  helpArgs = args[0].lower()
  if helpArgs == 'dm':
    bot.send_message(chat_id = update.message.chat_id, text = "Do you want to know what a DungeonMaster can here? I'll tell you.\nThe DM (short for DungeonMaster, similar to a GameMaster) creates the lobby and invites his players via a link. When the players chat with each other or roll dice, the DM always gets these messages and to whom it was sent. When the DM makes a roll or chats, only the designated players will receive this. One special thing for the DM tho: if no player is checked to receive his message, rolls are just made for the DM while messages are sent like everyone is checked.")
  elif helpArgs == 'new':
    bot.send_message(chat_id = update.message.chat_id, text = "So you want to be the man who leads his players to despair? Nice decision. First, you create a new lobby with '/new'. Then I'll ask you about how you want to call this lobby. Alternatively you can type the name directly behind the '/new' command (eg '/new Bounty Hunter'). That's it. then you just send the link I give you to your players and they'll join (hopefully).")
  elif helpArgs == 'player':
    bot.send_message(chat_id = update.message.chat_id, text = "The poor souls tormented by the DM. Let me guide you as good as I can.\nWhen you got invited to a game, I will ask you about your character's name.\nIf you want to chat, make a choice, who you want to hear your voice.\nBut always keep in mind what you do, for the DM is always hearing you.\nYou have no choice and still want to text, the DM is the one who gets your message next.\nIf you want to leave, take my bet, this function comes soon, but hasn't been implemented yet.\n\nHave fun!")
  elif helpArgs == 'join':
    bot.send_message(chat_id = update.message.chat_id, text = "You just got invited to a game or are waiting for your DM to create a lobby? I introduce you about what you do then:\nWhen your DM created a link, he/she will send it to you either as a link for the bot or like 'Join [Game name]'. Either way you click on it and press start when you're here. Then I will ask you about your character's name. After you entered it, I will send you the lobby name and the DM's name in one message together with a selection field where you can choose who gets your messages. Remember, you are talking as your character to other characters. This bot is not suited for private conversations, because !CAUTION! the DM receives a copy of every message you send. He also knows who sent it and to whom it was sent. Same with rolls.")
  elif helpArgs == 'roll':
    bot.send_message(chat_id = update.message.chat_id, text = "You want to roll some dice? Great! Just type '/roll' and then text in this form '3d20' where the number behind the d stands for the die and the number before the d stands for the number of corresponding dice you want to roll.\nFor example: '/roll 2d10' would roll two ten-sided dice for you.\n\nYou can also combine different dice with that form: '/roll 2d6 + 4d8'\nThis way, you would roll (for example) two six-sided dice and four eight-sided dice.\n\nIf the d is missing (eg. '/roll d6 + 10') I'll treat it as a modifier. This input would result in one six-sided die added to 10.\n\nImportant: you can't throw more than 100 dice at once.")
  else:
    help(bot, update, [])

def main(updater):
  dispatcher = updater.dispatcher

  dbFuncs.initDB()

  newGame = ConversationHandler(
    entry_points = [CommandHandler('new', new, Filters.private, pass_args = True, pass_user_data = True)],
    states = {
      SETNAME: [MessageHandler(Filters.text&Filters.private, gameName, pass_user_data = True)]
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private)]
  )

  joinGame = ConversationHandler(
    entry_points = [CommandHandler('start', start, Filters.private, pass_args = True, pass_user_data = True), RegexHandler('^\/[0-9A-Za-z]{10}$', changeLobby, pass_user_data = True)],
    states = {
      SETNAME: [MessageHandler(Filters.text&Filters.private, playerName, pass_user_data = True)]
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private)]
  )

  leaveGame = ConversationHandler(
    entry_points = [CommandHandler('leave', leave, Filters.private, pass_user_data = True)],
    states = {
      SETNAME: [MessageHandler(Filters.text&Filters.private, leaveLobby, pass_user_data = True)]
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private)]
  )

  dispatcher.add_handler(joinGame)
  dispatcher.add_handler(newGame)
  dispatcher.add_handler(leaveGame)
  dispatcher.add_handler(CommandHandler('my', my, Filters.private))
  dispatcher.add_handler(CommandHandler('help', help, Filters.private, pass_args = True))
  dispatcher.add_handler(CommandHandler('roll', roll, Filters.private, pass_args = True, pass_user_data = True))
  dispatcher.add_handler(CommandHandler('open', open, Filters.private, pass_user_data = True))
  dispatcher.add_handler(CommandHandler('close', close, Filters.private, pass_user_data = True))
  dispatcher.add_handler(CallbackQueryHandler(editMessage, pass_user_data = True))
  dispatcher.add_handler(RegexHandler('^\/.*', regexSlash))
  dispatcher.add_handler(MessageHandler(Filters.text&Filters.private, handleText, pass_user_data = True))
  dispatcher.add_error_handler(error_callback)
  updater.start_polling()

  updater.idle()

  updater.stop()

  dbFuncs.close()


if __name__ == '__main__':
  from ..bottoken import getToken
  main(getToken())
