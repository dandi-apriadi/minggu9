from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    jsonify
)
from pymongo import MongoClient
import requests
from datetime import datetime
import os 
from os.path import join, dirname
from dotenv import load_dotenv

app = Flask(__name__)

dotenv_path = join(dirname(__file__),'.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Routes for main functionalities

@app.route('/')
def main():
    words_result = db.words.find({}, {'_id': False})
    words = []
    for word in words_result:
        definition = word['definitions'][0]['shortdef']
        definition = definition if type(definition) is str else definition[0]
        words.append({
            'word': word['word'],
            'definition': definition,
        })
    msg = request.args.get('msg')
    return render_template('index.html', words=words, msg=msg)

@app.route('/error/word_not_found')
def word_not_found():
    word = request.args.get('word')
    suggestions = request.args.getlist('suggestions')
    return render_template('error.html', word=word, suggestions=suggestions)

@app.route('/detail/<keyword>', methods=['GET', 'POST'])
def detail(keyword):
    if request.method == 'GET':
        api_key = "702a079c-0b13-40a9-a295-fa4730d91fb9"
        url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{keyword}?key={api_key}'
        response = requests.get(url)
        definitions = response.json()

        if not definitions:
            # Redirect to error page with suggestions if available
            suggestions = request.args.getlist('suggestions')
            return redirect(url_for('word_not_found', word=keyword, suggestions=suggestions))

        if type(definitions[0]) is str:
            # Redirect to error page with suggestions if available
            return redirect(url_for('word_not_found', word=keyword, suggestions=definitions))

        status = request.args.get('status_give', 'new')
        return render_template('detail.html', word=keyword, definitions=definitions, status=status)
    elif request.method == 'POST':
        # Handle saving example sentences
        json_data = request.get_json()
        word = json_data.get('word')
        text = json_data.get('text')

        if word and text:
            doc = {
                'word': word,
                'text': text,
                'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.examples.insert_one(doc)
            return jsonify({'result': 'success', 'msg': 'Example sentence saved successfully!'})
        else:
            return jsonify({'result': 'error', 'msg': 'Missing word or text parameters'})

@app.route('/api/save_word', methods=['POST'])
def save_word():
    json_data = request.get_json()
    word = json_data.get('word_give')
    definitions = json_data.get('definitions_give')

    doc = {
        'word': word,
        'definitions': definitions,
        'date': datetime.now().strftime('%Y%m%d'),
    }

    db.words.insert_one(doc)

    return jsonify({
        'result': 'success',
        'msg': f'the word, {word}, was saved!!!',
    })

@app.route('/api/delete_word', methods=['POST'])
def delete_word():
    word = request.form.get('word_give')
    # Delete examples associated with the word
    db.examples.delete_many({'word': word})
    # Delete the word itself
    db.words.delete_one({'word': word})
    
    return jsonify({
        'result': 'success',
        'msg': f'the word, {word}, and associated examples were deleted',
    })

@app.route('/api/get_exs', methods=['GET'])
def get_exs():
    word = request.args.get('word_give')
    examples_result = db.examples.find({'word': word})
    examples = [{'text': ex['text'], 'id': str(ex['_id'])} for ex in examples_result]
    return jsonify({'result': 'success', 'examples': examples})

@app.route('/api/save_ex', methods=['POST'])
def save_ex():
    json_data = request.get_json()
    word = json_data.get('word')
    text = json_data.get('text')

    if word and text:
        doc = {
            'word': word,
            'text': text,
            'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        db.examples.insert_one(doc)
        return jsonify({'result': 'success', 'msg': 'Example sentence saved successfully!'})
    else:
        return jsonify({'result': 'error', 'msg': 'Missing word or text parameters'})

@app.route('/api/delete_ex', methods=['POST'])
def delete_ex():
    ex_id = request.form.get('id')
    db.examples.delete_one({'_id': ex_id})
    return jsonify({'result': 'success', 'msg': 'Example sentence deleted successfully!'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
