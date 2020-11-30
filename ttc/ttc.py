import numpy as np
import scipy
from scipy import signal
from scipy import misc
from scipy import ndimage

from skimage.util import view_as_blocks
import matplotlib.pyplot as plt

from ttc.util import restrict
from ttc.util import uniform_blur
from ttc.util import make_even_size

def _solve_abc(Ex, Ey, Et, GG):
    Ex2 = np.multiply(Ex, Ex)
    Ey2 = np.multiply(Ey, Ey)
    GG2 = np.multiply(GG, GG)
    ExEy = np.multiply(Ex, Ey)
    GEx = np.multiply(GG, Ex)
    GEy = np.multiply(GG, Ey)

    ExEt = np.multiply(Ex, Et)
    EyEt = np.multiply(Ey, Et)
    GEt = np.multiply(GG, Et)
    
    A = np.array([
            [Ex2.sum(), ExEy.sum(), GEx.sum()],
            [ExEy.sum(), Ey2.sum(), GEy.sum()],
            [GEx.sum(), GEy.sum(), GG2.sum()],
        ])

    b = np.array([
            [-ExEt.sum()],
            [-EyEt.sum()],
            [-GEt.sum()]
        ])
    
    v = np.matmul(np.linalg.inv(A), b)

    return v

def _compute_Ex(E):
    Ex = np.zeros_like(E)
    Ex[:-1, :] = E[1:, :] - E[:-1, :]
    return Ex

def _compute_Ey(E):
    Ey = np.zeros_like(E)
    Ey[:, :-1] = E[:, 1:] - E[:, :-1]
    return Ey

def _compute_Et(E1, E2):
    return E2 - E1

def _compute_G(Ex, Ey):
    m, n = Ex.shape
    ci, cj = m // 2, n // 2

    X, Y = np.mgrid[0:m, 0:n]
    Xp = X - ci # (i - ci)
    Yp = Y - cj # (j - cj)
    
    return np.multiply(Xp, Ex) + np.multiply(Yp, Ey)

def solve_ttc(img1, img2):
    Ex = restrict(_compute_Ex(img2), 1)
    Ey = restrict(_compute_Ey(img2), 1)
    Et = restrict(_compute_Et(img1, img2), 1)
    G = _compute_G(Ex, Ey)
    v = _solve_abc(Ex, Ey, Et, G)
    
    if v[2] == 0:
        raise ZeroDivisionError
    x0 = -v[0] / v[2]
    y0 = -v[1] / v[2]
    T = 1 / v[2]
    
    return T[0], x0[0], y0[0], Ex, Ey, Et, v

def solve_ttc_multiscale(img1, img2, size=2):
    T_n, x0_n, y0_n, EX_n, EY_n, ET_n, v_n = solve_ttc(img1, img2)
    T_p, x0_p, y0_p, EX_p, EY_p, ET_p, v_p = T_n, x0_n, y0_n, EX_n, EY_n, ET_n, v_n

    T_p = T_n + 1

    k = 0
    while T_p > T_n and T_n > 0:
        T_p, x0_p, y0_p, EX_p, EY_p, ET_p, v_p = T_n, x0_n, y0_n, EX_n, EY_n, ET_n, v_n

        img1_ = restrict(uniform_blur(img1, size))
        img2_ = restrict(uniform_blur(img2, size))
        
        if min(img1_.shape) <= 6:
            break        
        
        T_n, x0_n, y0_n, EX_n, EY_n, ET_n, v_n = solve_ttc(img1_, img2_)
        
        img1 = img1_
        img2 = img2_
        k += 1

    return T_p, x0_p*k, y0_p*k, EX_p, EY_p, ET_p, v_p*k
