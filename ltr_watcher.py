import threading
try:
    from . import linuxtrack
except Exception: #ImportError
    import linuxtrack
import time

try:
    from talon import rctx
except ImportError:
    rctx = None

class Watcher(object):
    def __init__(self):
        self.started = False
        self.callbacks = set()

        self.running_cv = threading.Condition()
        self.running = True
        self.suspended = False
        self.last_cb_time = None

    def _ensure_started(self):
        if self.started:
            return

        self.started = True
        self.ltr = linuxtrack.load_ltr()
        if self.ltr is not None:
            self._spawn()

    def register(self, cb):
        self._ensure_started()
        self.callbacks.add(cb)
        if rctx is not None:
            rctx.register(lambda: self.callbacks.remove(cb))

    def suspend(self):
        self._ensure_started()
        with self.running_cv:
            self.running = False

    def wakeup(self):
        self._ensure_started()
        with self.running_cv:
            self.running = True
            self.running_cv.notify_all()

    def _run_callbacks(self, pose):
        t = time.perf_counter()
        if self.last_cb_time is not None:
            dt = t - self.last_cb_time
        else:
            dt = 0.0
        self.last_cb_time = t

        for cb in self.callbacks:
            cb(pose, dt)

    def _cleanup(self):
        self.ltr.shutdown()
        self.started = False

    def _serve(self):
        # print("Started")
        init_count = 0
        while True:
            with self.running_cv:
                if not self.running and not self.suspended:
                    self.ltr.suspend()
                    self.suspended = True
                if not self.running:
                    self.running_cv.wait()
                if self.running and self.suspended:
                    self.ltr.wakeup()
                    self.suspended = False

            res = self.ltr.wait(1000)
            # print("wait: ", res)
            if res != 1:
                state = self.ltr.tracking_state()
                if state == self.ltr.INITIALIZING:
                    init_count += 1

                if state == self.ltr.STOPPED or init_count > 5:
                    self._cleanup()
                    return
                continue

            # state = self.ltr._status_msg(self.ltr.c.ltr_get_tracking_state())
            # print(state)

            pose, blobs, res = self.ltr.get_pose_full()
            # print("pose: ", res)
            if res != 1 or len(blobs) < 3:
                continue

            self._run_callbacks(pose)

    def _spawn(self):
        t = threading.Thread(target=self._serve, args=())
        t.daemon = True
        t.start()

watcher = Watcher()

def _main():
    def cb(pose, dt):
        print(dt)

    watcher.register(cb)
    time.sleep(10)
    watcher.suspend()
    time.sleep(10)
    watcher.wakeup()
    time.sleep(10)

    # watcher.wakeup()
    # time.sleep(10)
    # watcher.wakeup()
    # time.sleep(10)
    # watcher.wakeup()
    # # watcher.suspend()
    # time.sleep(9)
    # watcher.wakeup()
    # time.sleep(9)

if __name__ == '__main__':
    _main()
