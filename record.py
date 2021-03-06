import numpy as np
import time
import cv2
from collections import deque
import win32api
import h5py
import threading
from utils.joyoutput import JoyOutput
from utils.get_screen import get_screen
from utils.fps_sync import FpsSync

is_running = True
fps_limit = 8
# 27 refers to ESC key
pause_key = 27
file_name = 'data/training_data.hdf5'
state_name = 'state'
action_name = 'action'
batch_size = 512
# openCV uses shape: (height, width)
image_size = (160, 120)
state_dim = (*image_size[::-1], 3)
action_dim = (1,)


def save_batch(state, action):
    assert len(state) == len(action) == batch_size

    with h5py.File(filepath) as f:
        if state_name not in f:
            f.create_dataset(
                state_name,
                (batch_size, *state_dim),
                maxshape=(None, *state_dim),
                chunks=(batch_size, *state_dim),
                data=state),
        else:
            f[state_name].resize(f[state_name].shape[0] + batch_size, axis=0)
            f[state_name][-batch_size:] = state

        if action_name not in f:
            f.create_dataset(
                action_name,
                (batch_size, action_dim[0]),
                maxshape=(None, action_dim[0]),
                chunks=(batch_size, action_dim[0]), data=action),
        else:
            f[action_name].resize(f[action_name].shape[0] + batch_size, axis=0)
            f[action_name][-batch_size:] = action

        assert f[state_name].shape[0] == f[action_name].shape[0]
        print('Saved batch of size: {} in {}\nCurrent data length: {}'
              .format(batch_size, file_name, f[state_name].shape[0]))


def record():
    # reset pause key listener
    win32api.GetAsyncKeyState(pause_key)
    iterations = 0
    state_buffer = []
    action_buffer = []
    joy_out = JoyOutput(0, calibrate_axes=(0,))
    fps_sync = FpsSync(fps_limit)

    for i in range(3)[::-1]:
        print('starting in {} seconds'.format(i), end='\r')
        time.sleep(1)
    print('\nRecording!')

    fps_sync.init()

    while(is_running):
        if win32api.GetAsyncKeyState(pause_key):
            print('\nstopped')
            break

        state = get_screen('Grand Theft Auto V')
        state = cv2.resize(state, image_size)
        print(np.shape(state))
        action = [joy_out.get_axis()]
        thread = None

        state_buffer.append(state)
        action_buffer.append(action)

        if len(state_buffer) >= batch_size or len(action_buffer) >= batch_size:
            if thread and thread.is_alive():
                thread.join()

            thread = threading.Thread(target=save_batch,
                                      args=(state_buffer, action_buffer))
            thread.start()
            state_buffer = []
            action_buffer = []

        iterations += 1
        if iterations % 10 == 0:
            print('fps: {}'.format(fps_sync.get_fps()), end='\r')

        fps_sync.sync()


record()
