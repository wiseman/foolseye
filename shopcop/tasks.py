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




RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
FINISHED = 'FINISHED'


class TaskQueue(object):
    def __init__(self, dir, max_retries=3):
        self.queue = Queue.PriorityQueue()
        self.max_retries = max_retries
        self.runner = None
        self.condvar = threading.Condition()
        self.dir = dir
        self.delay_runner = False
        
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        self.data_path = os.path.join(self.dir, 'queue.dat')
        
        if os.path.exists(self.data_path):
            self.load_from_file(self.data_path)

    def load_from_file(self, data_path):
        with self.condvar:
            self.delay_runner = True
            self.queue = Queue.PriorityQueue()
            with open(data_path, 'rb') as f:
                tasks = json.load(f)
                for task_dict in tasks:
                    d = {}
                    for k in task_dict: d[str(k)] = task_dict[k]
                    self._add_task(apply(Task, [], d))
            self.delay_runner = False
            self.start_runner()

    def save_to_file(self):
        task_dicts = []
        while not self.queue.empty():
            priority, task = self.queue.get()
            task_dicts += [task.to_dict()]
        with open(self.data_path, 'wb') as f:
            json.dump(task_dicts, f, ensure_ascii=True)

    def add_task(self, task):
        with self.condvar:
            self._add_task(task)
            self.save_to_file()

    def _add_task(self, task):
        self.queue.put((task.priority, task))
        print 'Added task %s to queue %s.' % (task, self)
        if (not self.delay_runner) and (not self.runner):
            self.start_runner()
        

    def process_task(self):
        priority, task = self.queue.get()
        print 'Processing task %s pri=%s in queue %s' % (task, priority, self)
        task.run()
        if not task.succeeded():
            if task.num_tries() <= self.max_retries:
                print 'Task %s failed with result=%s, numtries=%s; Re-qeueing.' % \
                      (task, task.result(), task.num_tries())
                self.add_task(task)
            else:
                print 'Task %s failed with result=%s, numtries=%s; GIVING UP.' % \
                      (task, task.result(), task.num_tries())
        else:
            print 'Task %s succeeded with result=%s, numtries=%s.' % \
                  (task, task.result(), task.num_tries())
        with self.condvar:
            self.save_to_file()
        return task

    def start_runner(self):
        print 'Starting runner for queue %s' % (self,)
        self.runner = threading.Thread(target=self.thread_run_fn)
        self.runner.start()

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
    
    
g_default_queue = None


def add_task(**kwargs):
    global g_default_queue
    task = apply(Task, [], kwargs)
    g_default_queue.add_task(task)
