from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
  return "ShuffleGram Running ✅"

def run():
    app.run(host='0.0.0.0', port =8080)

def Keep_alive():
  t= Thread(Target =Run)
  t.Start()