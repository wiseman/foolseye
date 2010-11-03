from flask import Flask, g
import pymongo
import datetime


class ShopcopApp(Flask):
  def __init__(self, import_name, static_path=None):
    Flask.__init__(self, import_name, static_path=static_path)
    self.taskqueue = None
    
  def run(self, host='127.0.0.1', port=5000, **options):
    if self.taskqueue is None:
      self.taskqueue = shopcop.tasks.TaskQueue(dir=app.config['TASK_QUEUE_DIR'])
    self.taskqueue.start()
    return Flask.run(self, host=host, port=port, **options)

app = ShopcopApp(__name__)
app.config.from_object('shopcop.config')
app.config.from_envvar('SHOPCOP_CONFIG', silent=True)


def connect_db(app=None):
  "Returns a new connection to the database."
  if app is None:
    app = shopcop.app
  connection = pymongo.Connection(app.config['DATABASE_CONNECTION'])
  db = connection[app.config['DATABASE_NAME']]
  return connection, db


@app.before_request
def before_request():
  "Get a connection to the database for each request."
  g.db_connection, g.db = connect_db()


@app.after_request
def after_request(response):
  "Closes the database connection at the end of the request."
  g.db_connection.end_request()
  return response

@app.template_filter()
def timestamp(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    now = datetime.datetime.utcnow()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default


import shopcop.views
import shopcop.tasks

import shopcop.tests
import shopcop.errorlevelanalysis
import shopcop.copymove
