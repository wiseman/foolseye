import Queue
import threading
import urllib2
import urlparse
import time


RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
FINISHED = 'FINISHED'


class TaskQueue(object):
    def __init__(self, max_retries=3):
        self.queue = Queue.PriorityQueue()
        self.max_retries = max_retries
        self.runner = None

    def add_task(self, task):
        self.queue.add((task.priority, task))
        print 'Added task %s to queue %s.' % (task, self)
        if not self.runner:
            self.start_runner()

    def process_task(self):
        task = self.queue.get()
        print 'Processing task %s in queue %s' % (task, self)
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
        return task

    def start_runner(self):
        print 'Starting runner for queue %s' % (self,)
        self.runner = threading.Thread(target=self.thread_run_fn)
        self.runner.start()

    def thread_run_fn(self):
        while True:
            self.process_task()
        


class Task(object):
    def __init__(self, payload=None, method='POST', name=None, params={}, url=None, priority=0):
        self.payload = payload
        self.method = method
        self.name = name
        self.params = params
        self.url = url
        self.priority = priority
        self.execution_records = []

    def run(self):
        execution_record = { 'time': time.time() }
        if self.method == 'GET':
            url = urlparse.urljoin(self.url, urllib.urlencode(params))
            response = urllib2.urlopen(url)
            status = response.code
            response.close()
        else:
            response = urllib2.urlopen(self.url, self.payload)
            status = response.code
            response.close()
        execution_record['status'] = status
        self.execution_records += execution_record

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
    
    
g_default_queue = TaskQueue()

def add_task(**kwargs):
    global g_default_queue
    task = apply(Task, [], kwargs)
    g_default_queue.add_task(task)
