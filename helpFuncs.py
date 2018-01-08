from random import choice
from string import (ascii_lowercase, ascii_uppercase, digits)
from bottoken import getConn
import psycopg2

conn = None
cur = None

def id_generator(size=10, chars = ascii_lowercase + ascii_uppercase + digits):
  return ''.join(choice(chars) for _ in range(size))

def correctArgs(args):
  if len(args) == 1:
    return args[0]
  elif "[" in str(args):
    return " ".join(args)
  return str(args)

def initDB():
  global conn
  global cur
  conn = getConn()
  cur = conn.cursor()
  conn.rollback()
  cur.execute("CREATE TABLE IF NOT EXISTS Games(Code TEXT PRIMARY KEY NOT NULL, Title TEXT NOT NULL, DM BIGINT NOT NULL);")
  cur.execute("CREATE TABLE IF NOT EXISTS Current(Player BIGINT PRIMARY KEY NOT NULL, Game TEXT REFERENCES Games, Message BIGINT);")
  cur.execute("CREATE TABLE IF NOT EXISTS Players(Player BIGINT NOT NULL REFERENCES Current, Character TEXT NOT NULL, Code TEXT REFERENCES Games);")
  conn.commit()

def isAvailable(code):
  cur.execute("SELECT Code FROM Games WHERE Code = %s;", (code,))
  test = cur.fetchall()
  if len(test) == 0:
    return False
  return True

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

def initCurrent(player):
  cur.execute("INSERT INTO Current(Player) VALUES(%s) ON CONFLICT(Player) DO NOTHING;", (player,))
  conn.commit()

def getOwnCharacter(player, code):
  cur.execute("SELECT Character FROM Players WHERE Player = %s AND Code = %s;", (player, code))
  return evaluateOne(cur.fetchone())

def getPlayers(code):
  cur.execute("SELECT Player FROM Players WHERE Code = %s ORDER BY Player;", (code,))
  return evaluateList(cur.fetchall())

def getPlayerCharas(code):
  cur.execute("SELECT Character FROM Players WHERE Code = %s ORDER BY Player;", (code,))
  return evaluateList(cur.fetchall())

def getCurrentLobby(player):
  cur.execute("SELECT Game FROM Current WHERE Player = %s;", (player,))
  return evaluateOne(cur.fetchone())

def getDM(code):
  cur.execute("SELECT DM FROM Games WHERE Code = %s;", (code,))
  return evaluateOne(cur.fetchone())

def getLobbyTitle(code):
  cur.execute("SELECT Title FROM Games WHERE Code = %s;", (code,))
  return evaluateOne(cur.fetchone())

def updateMessageInCurrent(player, message):
  cur.execute("UPDATE Current SET Message = %s WHERE Player = %s;", (message, player))
  conn.commit()

def getCurrentMessage(player):
  cur.execute("SELECT Message FROM Current WHERE Player = %s;", (player,))
  return evaluateOne(cur.fetchone())

def updateGameInCurrent(player, code):
  cur.execute("UPDATE Current SET Game = %s WHERE Player = %s;", (code, player))
  conn.commit()

def insertGame(code, title, dm):
  cur.execute("INSERT INTO Games(Code, Title, DM) VALUES(%s, %s, %s);", (code, title, dm))
  cur.execute("UPDATE Current SET Game = %s WHERE Player = %s;", (code, dm))
  conn.commit()

def insertPlayers(player, character, code):
  cur.execute("INSERT INTO Players(Player, Character, Code) VALUES(%s, %s, %s);", (player, character, code))
  conn.commit()

def close():
  conn.close()
