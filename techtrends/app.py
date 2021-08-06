# import logging
import logging
import sys
import os
import sqlite3

from flask import Flask, json, render_template, request, url_for, redirect, flash

conn_counter = 0


# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    global conn_counter
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    conn_counter += 1
    return connection


# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                              (post_id,)).fetchone()
    connection.close()
    return post


# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'


# Define the main route of the web application
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)


# Define how each individual article is rendered
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.error('Post with id {} not found'.format(post_id))
        return render_template('404.html'), 404
    else:
        app.logger.debug('Getting post with title: {}'.format(post[2]))
        return render_template('post.html', post=post)


# Define the About Us page
@app.route('/about')
def about():
    app.logger.debug('Retrieving "About Us" page')
    return render_template('about.html')


# Define the post creation functionality
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                               (title, content))
            connection.commit()
            connection.close()

            app.logger.debug('Article {} was created'.format(title))

            return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/healthz')
def healthcheck():
    try:
        connection = get_db_connection()
        connection.execute('SELECT * FROM posts WHERE id = ?',
                           (1,)).fetchall()
        connection.close()
        response = app.response_class(
            response=json.dumps({"result": 200}),
            status=200,
            mimetype='application/json'
        )
        return response
    except sqlite3.OperationalError:
        app.logger.exception('No table found in the database')
        response = app.response_class(
            response=json.dumps({"error": "unhealthy"}),
            status=500,
            mimetype='application/json'
        )
        return response


@app.route('/metrics')
def metrics():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()

    response = app.response_class(
        response=json.dumps(
            {"status": "success", "code": 0, "data": {"db_connection_count": conn_counter, "post_count": len(posts)}}),
        status=200,
        mimetype='application/json'
    )

    app.logger.info('Metrics request successfull')
    return response


# start the application on port 3111
if __name__ == "__main__":
    loglevel = os.getenv("LOGLEVEL", "DEBUG").upper()
    loglevel = (
        getattr(logging, loglevel)
        if loglevel in ["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING", ]
        else logging.DEBUG
    )
    # Set logger to handle STDOUT and STDERR

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)

    handlers = [stderr_handler, stdout_handler]
    # format output
    format_output = '%(asctime)s - %(message)s - %(levelname)s(%(name)s)'
    logging.basicConfig(format=format_output, level=loglevel, handlers=handlers)
    app.run(host='0.0.0.0', port='3111')
