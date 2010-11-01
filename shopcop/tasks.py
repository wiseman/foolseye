import Queue
import threading
import urllib
import urllib2
import urlparse
import time
import os
import os.path
import json

from shopcop import app


class TaskQueue(object):
    def __init__(self, dir, max_retries=3):
        self.dir = dir
        self.max_retries = max_retries
        self.queue = []
        self.runner = None
        self.condvar = threading.Condition()
        
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        self.data_path = os.path.join(self.dir, 'queue.dat')
        
        if os.path.exists(self.data_path):
            self.load_from_file()

    def load_from_file(self):
        with open(self.data_path, 'rb') as f:
            data = json.load(f)
            self.queue = [Task.from_dict(d) for d in data]
        
    def save_to_file(self):
        task_dicts = [t.to_dict() for t in self.queue]
        with open(self.data_path, 'wb') as f:
            json.dump(task_dicts, f, ensure_ascii=True)

    def add_task(self, task):
        with self.condvar:
            self.queue = self.queue + [task]
            print 'Added task %s to queue %s.' % (task, self)
            self.save_to_file()
            self.condvar.notifyAll()

    def process_task(self):
        with self.condvar:
            while len(self.queue) == 0:
                self.condvar.wait()
            task = self.queue[0]
        print 'Processing task %s in queue %s' % (task, self)
        start_time = time.time()
        task.run()
        duration = time.time() - start_time
        if not task.succeeded():
            if task.num_tries() <= self.max_retries:
                print 'Task %s failed with result=%s in %s s, numtries=%s; Re-qeueing.' % \
                      (task, task.result(), duration, task.num_tries())
                self.add_task(task)
            else:
                print 'Task %s failed with result=%s in %s s, numtries=%s; GIVING UP.' % \
                      (task, task.result(), duration, task.num_tries())
        else:
            print 'Task %s succeeded with result=%s in %s s, numtries=%s.' % \
                  (task, task.result(), duration, task.num_tries())

        with self.condvar:
            self.load_from_file()
            self.queue = self.queue[1:]
            self.save_to_file()
        return task

    def ensure_runner(self):
        if self.runner is None:
            print 'Starting runner for queue %s' % (self,)
            self.runner = threading.Thread(target=self.thread_run_fn)
            self.runner.daemon = True
            self.runner.start()

    def start(self):
        self.ensure_runner()

    def thread_run_fn(self):
        while True:
            self.process_task()
        


class Task(object):
    def __init__(self, payload=None, method='POST', name=None, params={}, url=None, priority=0, execution_records=[]):
        self.payload = payload
        self.method = method
        self.name = name
        self.params = params
        self.url = url
        self.priority = priority
        self.execution_records = execution_records

    def to_dict(self):
        d = {}
        for a in ['payload', 'method', 'name', 'params', 'url', 'priority', 'execution_records']:
            d[a] = getattr(self, a)
        return d

    @staticmethod
    def from_dict(d):
        dict = {}
        for k in d: dict[str(k)] = d[k]
        return apply(Task, [], dict)

    def __str__(self):
        if self.params:
            return '<Task %s?%s>' % (self.url, urllib.urlencode(self.params))
        else:
            return '<Task %s>' % (self.url,)

    def run(self):
        execution_record = { 'time': time.time() }
        if self.method == 'GET':
            url = self.url + '?' + urllib.urlencode(self.params)
            status = self.open_url(url)
        else:
            status = self.open_url(self.url, self.payload)
        execution_record['status'] = status
        self.execution_records += [execution_record]

    def open_url(self, *args, **kwargs):
        try:
            response = urllib2.urlopen(*args, **kwargs)
            response.close()
            return response.code
        except urllib2.HTTPError, e:
            return e.code

    def succeeded(self):
        if self.num_tries() == 0:
            return False
        status = self.execution_records[-1]['status']
        return status >= 200 and status <= 299

    def num_tries(self):
        return len(self.execution_records)

    def result(self):
        if self.num_tries() == 0:
            return None
        return self.execution_records[-1]['status']
    
    
