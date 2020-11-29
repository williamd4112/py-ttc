import argparse
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import numpy as np
import scipy
from scipy import signal
from scipy import misc
from scipy import ndimage

from skimage.util import view_as_blocks

import cv2

from ttc import solve_ttc_multiscale, solve_ttc
from ttc.util import load_video, uniform_blur, restrict
from ttc.logger import TTCLogger

from PIL import Image
import io

def img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it"""
    import io
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', type=str, default='test.mp4',
                        help='Source video')
    parser.add_argument('--dst', type=str, default='test.csv',
                        help='Log path')
    parser.add_argument('--dst-gif', type=str, default='animation.gif',
                        help='Output path of GIF file')
    parser.add_argument('--size', type=int, default=5)
    parser.add_argument('--vis', action='store_true', default=False)
    parser.add_argument('--use-multiscale', action='store_true', default=False)
    parser.add_argument('--filter-outlier', action='store_true', default=False)
    args = parser.parse_args()

    # For plotting
    fig = plt.figure()
    plt.gray()
    ax1 = fig.add_subplot(331) 
    ax1.set_axis_off()
    ax2 = fig.add_subplot(332) 
    ax2.set_axis_off()
    ax3 = fig.add_subplot(333)  
    ax3.set_axis_off()
    ax4 = fig.add_subplot(334)
    ax5 = fig.add_subplot(335)
    ax5.set_axis_off()
    ax6 = fig.add_subplot(336)
    ax6.set_axis_off()
    FOE_marker = None
    Ts = []
    imgs = []

    # For logging
    logger = TTCLogger(args.dst)

    prev_frame = None
    for frame in load_video(args.src):
        frame = restrict(frame)
        m, n = frame.shape
        frame = uniform_blur(frame, args.size)

        if prev_frame is not None:
            start_time = time.time()
            if args.use_multiscale:
                T, x0, y0, Ex, Ey, Et, v = solve_ttc_multiscale(prev_frame, frame)
            else:
                T, x0, y0, Ex, Ey, Et, v = solve_ttc(prev_frame, frame)
            elapsed_time = time.time() - start_time

            if args.filter_outlier and (T > 1e5 or T < 0):
               continue

            logger.log(T, x0 + (n) / 2, y0 + (m) / 2, v[0][0], v[1][0], v[2][0])
            print('Elapsed time = {} sec; TTC = {}; FoE = {}; A = {:2f}, B = {:2f}, C = {:2f}'.format(elapsed_time, T, 
                                    (x0 + (n) / 2, y0 + (m) / 2),
                                    v[0][0], v[1][0], v[2][0]))

            if args.vis:
                Ts.append(T)
                ax1.imshow(Ex)
                ax1.set_title('Ex')
                ax2.imshow(Ey)
                ax2.set_title('Ey')
                ax3.imshow(Et)
                ax3.set_title('Et')
                ax4.plot(Ts, color='b')
                ax4.set_title('TTC')
                ax5.imshow(prev_frame)
                ax5.set_title('Frame (t-1)')
                ax6.imshow(frame)
                ax6.set_title('Frame (t)')
                
                if FOE_marker is not None:
                    FOE_marker.remove()

                FOE_marker = ax6.annotate('X', 
                            (x0+(n)/2, y0+(m)/2), 
                            textcoords="offset points", 
                            xytext=(0,0), 
                            color='r',
                            ha='center') 
                plt.draw()
                plt.pause(0.00001)
                imgs.append(img(fig))
        
        prev_frame = frame

    if args.vis:
        fp_out = args.dst_gif
        imgs[0].save(fp=fp_out, format='GIF', append_images=imgs,
            save_all=True, duration=200, loop=0)
