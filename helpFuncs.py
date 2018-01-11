from random import (choice, randint)
from string import (ascii_lowercase, ascii_uppercase, digits)
from re import search

def id_generator(size=10, chars = ascii_lowercase + ascii_uppercase + digits):
  return ''.join(choice(chars) for _ in range(size))

def correctArgs(args):
  if len(args) == 1:
    return args[0]
  elif "[" in str(args):
    return " ".join(args)
  return str(args)

#TODO finish parser
def diceParser(args):
  dice = []
  die = []
  for i in args:
    try:
      d = search('d|D|w|W', i).start()
    except AttributeError:
      if is_int(i):
        dice.append(0)
        die.append(int(i))
        continue
      return "Please use the following formatting:\n'/roll xdy' where x is the amount of dice and y is the die you want to roll. And don't forget to use integers."
    if d == 0:
      if is_int(i[d+1:]):
        dice.append(1)
        die.append(int(i[d+1:]))
      else:
        return "Please use the following formatting:\n'/roll xdy' where x is the amount of dice and y is the die you want to roll. And don't forget to use integers."
    else:
      if is_int(i[:d]) and is_int(i[d+1:]):
        dice.append(int(i[:d]))
        die.append(int(i[d+1:]))
      else:
        return "Please use the following formatting:\n'/roll xdy' where x is the amount of dice and y is the die you want to roll. And don't forget to use integers."
  if sum(dice) > 20:
    return "I can't imagine in which situation you roll more than 20 dice (unless it's some homebrewed epic overpowered mastersword or something). Please use a maximum of 20 dice per roll."
  theText = "Rolled: {0}".format(str(dice[0]) + 'D' + str(die[0]))
  for i in range(len(dice)):
    if i == 0:
      continue
    theText += " + "
    if dice[i] != 0:
      theText += str(dice[i]) + "D"
    theText += str(die[i])
  theText += "\nResult:\n"
  results = []
  for i in range(len(dice)):
    if dice[i] == 0:
      results.append(die[i])
    for j in range(dice[i]):
      results.append(randint(1, die[i]))
  theText += str(sum(results)) + " = " + str(results[0])
  results.pop(0)
  for i in results:
    theText += " + " + str(i)
  return theText

def is_int(number):
  try:
    int(number)
    return True
  except ValueError:
    return False
