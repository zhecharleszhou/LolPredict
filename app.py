from flask import Flask, render_template, request, redirect

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('parallax.html')

@app.route('/', methods=['POST'])
def my_form_post():
    text = request.form['summonerName']
    text2 = request.form['champName']
    processed_text = text.upper()
    processed_text2 = text.upper()
    return 'You entered: ' + processed_text + ' ' + processed_text2

@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(port=33507)
