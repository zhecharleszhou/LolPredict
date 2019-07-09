from flask import Flask, render_template, request, redirect

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('parallax.html')

@app.route('/', methods=['POST'])
def my_form_post():
    sumNameText = request.form['summonerName']
    champNameText = request.form['champName']
    processed_sumName = sumNameText.upper()
    processed_champName = champNameText.upper()
    return 'You entered: ' + processed_sumName + ' ' + processed_champName

@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(port=33507)
