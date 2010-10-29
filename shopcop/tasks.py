import threading

RUNNING = 'RUNNING'
STOPPED = 'STOPPED'
FINISHED = 'FINISHED'


class AsyncTask:
    def __init__(self, function, args=[], kwargs={}):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.thread = threading.Thread(target=self.thread_fn)
        self.result = None
        self.status = STOPPED
        self.condvar = threading.Condition()

    def thread_fn(self):
        result = apply(self.function, self.args, self.kwargs)
        with self.condvar:
            self.result = result
            self.status = FINISHED
            self.condvar.notify_all()

    def start(self):
        self.thread.start()

    def get_result(self):
        with self.condvar:
            while not self.status == FINISHED:
                self.condvar.wait()
        return self.result


