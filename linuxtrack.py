from cffi import FFI
import time
import os
from collections import namedtuple

CDEF = """
typedef enum {
  ltr_OK = 0,
  INITIALIZING = 1,
  RUNNING = 2,
  PAUSED = 3,
  STOPPED = 4,
  //Error codes
  err_NOT_INITIALIZED = -1,
  err_SYMBOL_LOOKUP = -2,
  err_NO_CONFIG = -3,
  err_NOT_FOUND = -4,
  err_PROCESSING_FRAME = -5
}ltr_state_type;

ltr_state_type ltr_init(const char *cust_section);
ltr_state_type ltr_shutdown(void);
ltr_state_type ltr_suspend(void);
ltr_state_type ltr_wakeup(void);
ltr_state_type ltr_recenter(void);
ltr_state_type ltr_get_tracking_state(void);

int ltr_get_pose(float *heading,
                 float *pitch,
                 float *roll,
                 float *tx,
                 float *ty,
                 float *tz,
                 uint32_t *counter);


typedef struct{
  float pitch;
  float yaw;
  float roll;
  float tx;
  float ty;
  float tz;
  uint32_t counter;
  uint32_t resolution_x;
  uint32_t resolution_y;
  float raw_pitch;
  float raw_yaw;
  float raw_roll;
  float raw_tx;
  float raw_ty;
  float raw_tz;
  uint8_t status;
} ltr_pose_t;

int ltr_get_pose_full(ltr_pose_t *pose, float blobs[], int num_blobs, int *blobs_read);

int ltr_get_abs_pose(float *heading,
                    float *pitch,
                    float *roll,
                    float *tx,
                    float *ty,
                    float *tz,
                    uint32_t *counter);

ltr_state_type ltr_request_frames(void);
int ltr_get_frame(int *req_width, int *req_height, size_t buf_size, uint8_t *buffer);
ltr_state_type ltr_notification_on(void);
int ltr_get_notify_pipe(void);
int ltr_wait(int timeout);
"""


Pose = namedtuple("Pose", "raw_pitch raw_yaw raw_roll raw_tx raw_ty raw_tz")

class Linuxtrack(object):
    INITIALIZING = 1
    RUNNING = 2
    PAUSED = 3
    STOPPED = 4

    def __init__(self, libpath):
        self.ffi = FFI()
        self.ffi.cdef(CDEF)
        self.c = self.ffi.dlopen(libpath)
        self._check(self.c.ltr_init(self.ffi.NULL))
        self._check(self.c.ltr_notification_on())

    def shutdown(self):
        self._check(self.c.ltr_shutdown())
        # print("Shutdown")

    def suspend(self):
        return self._check(self.c.ltr_suspend())

    def wakeup(self):
        return self._check(self.c.ltr_wakeup())

    def wait(self,timeout):
        return self._check(self.c.ltr_wait(timeout))

    def tracking_state(self):
        return self.c.ltr_get_tracking_state()

    def get_pose_full(self):
        blobs = self.ffi.new("float[9]")
        pose = self.ffi.new("ltr_pose_t *")
        blobs_read = self.ffi.new("int *")
        res = self._check(self.c.ltr_get_pose_full(pose, blobs, 3, blobs_read))

        actual_blobs = [[blobs[i*3], blobs[i*3+1], blobs[i*3+2]] for i in range(blobs_read[0])]
        py_pose = Pose(pose.raw_pitch, pose.raw_yaw, pose.raw_roll, pose.raw_tx, pose.raw_ty, pose.raw_tz)
        return py_pose, actual_blobs, res

    def _status_msg(self, res):
        if res == self.c.INITIALIZING:
          return "Linuxtrack is initializing.";
        elif res == self.c.RUNNING:
          return "Linuxtrack is running.";
        elif res == self.c.PAUSED:
          return "Linuxtrack is paused.";
        elif res == self.c.STOPPED:
          return "Linuxtrack is stopped.";
        elif res == self.c.err_NOT_INITIALIZED:
          return "Linuxtrack function was called without proper initialization.";
        elif res == self.c.err_SYMBOL_LOOKUP:
          return "Internal error (symbol lookup).";
        elif res == self.c.err_NO_CONFIG:
          return "Linuxtrack config not found."
        elif res == self.c.err_NOT_FOUND:
          return "Linuxtrack was removed or relocated."
        elif res == self.c.err_PROCESSING_FRAME:
          return "Internal error (frame processing)."
        else:
            return "UNKNOWN status code: {}".format(res)

    def _check(self, res):
        if res < 0:
            raise Exception(self._status_msg(res))
        return res


def _find_lib():
    # TODO search all the places linuxtrack.c looks
    path = "/Applications/ltr_gui.app/Contents/Frameworks/liblinuxtrack.0.dylib"
    if os.path.isfile(path):
        return path

    return None

def load_ltr():
    libpath = _find_lib()
    if libpath is None:
        return None

    return Linuxtrack(libpath)

def _main():
    ltr = load_ltr()
    ltr.wait(5000)
    ltr.wait(3000)
    pose, blobs, res = ltr.get_pose_full()
    ltr.wait(3000)
    pose, blobs, res = ltr.get_pose_full()
    print(pose)
    print(blobs)
    ltr.suspend()
    time.sleep(5)
    ltr.wakeup()
    ltr.wait(3000)
    print(ltr.get_pose_full())
    print("Done")


if __name__ == '__main__':
    _main()
