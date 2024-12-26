from flask import Flask, render_template, jsonify
from scraper.twitter_selenium import TwitterScraper 
import traceback
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['twitter_trends'] 
collection = db['trending_topics'] 

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/trending', methods=['POST'])
def get_trending():
    try:
        scraper = TwitterScraper()
        result = scraper.scrape_twitter() 
        
        trending_data = {
            '_id': result['_id'],
            'date_time': result['date_time'],
            'ip_address': result['ip_address'],
            'trends': result['trends']
        }
        
        return jsonify(trending_data), 200 
    except Exception as e:
        error_message = f"Error occurred during scraping: {str(e)}"
        print(traceback.format_exc())
        return jsonify({'error': error_message}), 500

@app.route('/get_trends', methods=['GET'])
def get_trends_from_db():
    try:
        all_trends = list(collection.find())  
        
        for trend in all_trends:
            trend['_id'] = str(trend['_id'])
        
        if all_trends:
            return jsonify(all_trends), 200
        else:
            return jsonify({'error': 'No trending data found'}), 404
    except Exception as e:
        error_message = f"Error occurred while fetching from the database: {str(e)}"
        print(traceback.format_exc())
        return jsonify({'error': error_message}), 500

        
if __name__ == '__main__':
    app.run(debug=True)
