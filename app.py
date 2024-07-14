from flask import Flask, render_template, request, jsonify
from flask_cors import CORS, cross_origin
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import logging
import pymongo
import csv

logging.basicConfig(filename="scrapper.log", level=logging.INFO)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def homepage():
    return render_template("index.html")

@app.route("/review", methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            searchString = request.form['content'].replace(" ", "")
            flipkart_url = "https://www.flipkart.com/search?q=" + searchString
            uClient = uReq(flipkart_url)
            flipkartPage = uClient.read()
            uClient.close()
            flipkart_html = bs(flipkartPage, "html.parser")
            bigboxes = flipkart_html.findAll("div", {"class": "cPHDOP col-12-12"})
            logging.info(f"Found {len(bigboxes)} big boxes")
            del bigboxes[0:3]

            if not bigboxes:
                return "No products found", 404

            box = bigboxes[0]
            productLink = "https://www.flipkart.com" + box.div.div.div.a['href']
            prodRes = requests.get(productLink)
            prodRes.encoding = 'utf-8'
            prod_html = bs(prodRes.text, "html.parser")
            commentboxes = prod_html.find_all('div', {'class': "RcXBOT"})
            logging.info(f"Found {len(commentboxes)} comment boxes")

            filename = searchString + ".csv"
            fw = open(filename, "w")
            headers = "Product, Customer Name, Rating, Heading, Comment \n"
            fw.write(headers)
            reviews = []

            for i, commentbox in enumerate(commentboxes):
                try:
                    name = commentbox.div.div.find_all('p', {'class': '_2NsDsF AwS1CA'})[0].text
                except (AttributeError, IndexError) as e:
                    name = "No Name"
                    logging.info(f"Name not found in commentbox {i}: {e}")

                try:
                    rating = commentbox.div.div.div.div.text
                except (AttributeError, IndexError) as e:
                    rating = 'No Rating'
                    logging.info(f"Rating not found in commentbox {i}: {e}")

                try:
                    commentHead = commentbox.div.div.div.p.text
                except (AttributeError, IndexError) as e:
                    commentHead = 'No Comment Heading'
                    logging.info(f"Comment heading not found in commentbox {i}: {e}")

                try:
                    comtag = commentbox.div.div.find_all('div', {'class': ''})
                    custComment = comtag[0].div.text
                except (AttributeError, IndexError) as e:
                    custComment = 'No Comment'
                    logging.info(f"Customer comment not found in commentbox {i}: {e}")

                mydict = {"Product": searchString, "Name": name, "Rating": rating, "CommentHead": commentHead,
                          "Comment": custComment}
                reviews.append(mydict)

            logging.info("log my final result {}".format(reviews))

            # MongoDB connection
            try:
                client = pymongo.MongoClient("mongodb+srv://ravisharma:ravi6143@cluster0.ukbminh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
                db = client['scrapping']
                review_col = db['review_data']
                review_col.insert_many(reviews)
                logging.info("Data inserted into MongoDB successfully")
            except pymongo.errors.OperationFailure as e:
                logging.error(f"MongoDB Authentication Error: {e.details}")
                return 'MongoDB authentication failed', 500
            except Exception as e:
                logging.error(f"MongoDB Connection Error: {e}")
                return 'Failed to connect to MongoDB', 500

            return render_template('result.html', reviews=reviews[0:(len(reviews) - 1)])
        except Exception as e:
            logging.error(f"Error: {e}")
            return 'Something went wrong'

    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
