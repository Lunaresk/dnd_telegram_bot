from bottoken import getConn
import psycopg2

conn = None
cur = None

def initDB():
  global conn
  global cur
  conn = getConn()
  cur = conn.cursor()
  conn.rollback()
  cur.execute("CREATE TABLE IF NOT EXISTS Games(Code TEXT PRIMARY KEY NOT NULL, Title TEXT NOT NULL, DM BIGINT NOT NULL, Open BOOLEAN NOT NULL DEFAULT TRUE);")
  cur.execute("CREATE TABLE IF NOT EXISTS Current(Player BIGINT PRIMARY KEY NOT NULL, Game TEXT REFERENCES Games, Message BIGINT, SendTo Text);")
  cur.execute("CREATE TABLE IF NOT EXISTS Players(Player BIGINT NOT NULL REFERENCES Current, Character TEXT NOT NULL, Code TEXT REFERENCES Games);")
  conn.commit()

def isAvailable(code):
  cur.execute("SELECT Code FROM Games WHERE Code = %s;", (code,))
  test = evaluateOne(cur.fetchone())
  if test != None:
    return True
  return False

def isOpen(code):
  cur.execute("SELECT IsOpen FROM Games WHERE Code = %s;", (code,))
  test = evaluateOne(cur.fetchone())
  if test != None:
    return test
  return False

def initCurrent(player):
  cur.execute("INSERT INTO Current(Player) VALUES(%s) ON CONFLICT(Player) DO NOTHING;", (player,))
  conn.commit()

def updateMessageInCurrent(player, message):
  cur.execute("UPDATE Current SET Message = %s WHERE Player = %s;", (message, player))
  conn.commit()

def updateGameInCurrent(player, code):
  cur.execute("UPDATE Current SET Game = %s WHERE Player = %s;", (code, player))
  conn.commit()

def updateSendtoInCurrent(player, sendto):
  dbEntry = []
  for i in sendto:
    dbEntry.append(str(i))
  cur.execute("UPDATE Current SET SendTo = %s WHERE Player = %s;", (','.join(dbEntry), player))
  conn.commit()

def getCurrentMessage(player):
  cur.execute("SELECT Message FROM Current WHERE Player = %s;", (player,))
  return evaluateOne(cur.fetchone())

def getCurrentLobby(player):
  cur.execute("SELECT Game FROM Current WHERE Player = %s;", (player,))
  return evaluateOne(cur.fetchone())

def getCurrentSendto(player):
  cur.execute("SELECT SendTo FROM Current WHERE Player = %s;", (player,))
  theList = evaluateOne(cur.fetchone())
  if theList == None:
    return []
  theList = theList.split(',')
  for i in range(len(theList)):
    theList[i] = int(theList[i])
  return theList

def getAllUsers():
  cur.execute("SELECT Player FROM Current;")
  return evaluateList(cur.fetchall())

def insertGame(code, title, dm):
  cur.execute("INSERT INTO Games(Code, Title, DM) VALUES(%s, %s, %s);", (code, title, dm))
  cur.execute("UPDATE Current SET Game = %s WHERE Player = %s;", (code, dm))
  conn.commit()

def getLobbyTitle(code):
  cur.execute("SELECT Title FROM Games WHERE Code = %s;", (code,))
  return evaluateOne(cur.fetchone())

def getDM(code):
  cur.execute("SELECT DM FROM Games WHERE Code = %s;", (code,))
  return evaluateOne(cur.fetchone())

def closeLobby(code):
  cur.execute("UPDATE Games SET isOpen = FALSE WHERE Code = %s;", (code,))
  conn.commit()

def openLobby(code):
  cur.execute("UPDATE Games SET isOpen = TRUE WHERE Code = %s;", (code,))
  conn.commit()

def removeGame(code):
  cur.execute("DELETE FROM Players WHERE Code = %s;", (code,))
  cur.execute("UPDATE Current SET Message = DEFAULT WHERE Game = %s;", (code,))
  cur.execute("UPDATE Current SET Game = DEFAULT WHERE Game = %s;", (code,))
  cur.execute("DELETE FROM Games WHERE Code = %s;", (code,))
  conn.commit()

def insertPlayers(player, character, code):
  cur.execute("INSERT INTO Players(Player, Character, Code) VALUES(%s, %s, %s);", (player, character, code))
  conn.commit()

def getPlayers(code):
  cur.execute("SELECT Player FROM Players WHERE Code = %s ORDER BY Player;", (code,))
  return evaluateList(cur.fetchall())

def getPlayerCharas(code):
  cur.execute("SELECT Character FROM Players WHERE Code = %s ORDER BY Player;", (code,))
  return evaluateList(cur.fetchall())

def getOwnCharacter(player, code):
  cur.execute("SELECT Character FROM Players WHERE Player = %s AND Code = %s;", (player, code))
  return evaluateOne(cur.fetchone())

def getGames(player):
  cur.execute("SELECT Code FROM Games WHERE DM = %s;", (player,))
  temp1 = evaluateList(cur.fetchall())
  cur.execute("SELECT Code FROM Players WHERE Player = %s;", (player,))
  temp2 = evaluateList(cur.fetchall())
  if temp1 == None:
    if temp2 == None:
      return None
    return temp2
  if temp2 == None:
    return temp1
  return temp1 + temp2

def removePlayerFromGame(player, game):
  cur.execute("DELETE FROM Players WHERE Code = %s AND Player = %s;", (game, player))
  cur.execute("UPDATE Current SET Message = DEFAULT WHERE Game = %s AND Player = %s;", (game, player))
  cur.execute("UPDATE Current SET Game = DEFAULT WHERE Game = %s AND Player = %s;", (game, player))
  conn.commit()

def evaluateList(datas):
  cur.fetchall()
  list = []
  for i in datas:
    list.append(i[0])
  if len(list) == 0:
    return None
  return list

def evaluateOne(data):
  cur.fetchall()
  if data != None:
    if data[0] != None:
      return data[0]
  return None

def close():
  conn.close()
