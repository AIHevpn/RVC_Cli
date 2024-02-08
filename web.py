from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    model_link = request.form['model_link']
    # Add the logic for downloading and configuring the model here
    
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True, share=True)
