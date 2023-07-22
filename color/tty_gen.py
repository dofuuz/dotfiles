# -*- coding: utf-8 -*-
"""
Created on Mon Mar 14 13:31:12 2022

@author: dof
"""

from collections import OrderedDict
import csv
import json

import matplotlib.pylab as plt
import numpy as np

from color_oklab import linear_srgb_to_oklch, oklch_to_linear_srgb
from color_oklab import gamut_clip_adaptive_L0_0_5
from color_srgb import lin_srgb_to_srgb, srgb_to_lin_srgb


REF_COLOR = 9   # xterm color scheme

np.set_printoptions(precision=3, suppress=True)


with open('tty_color.tsv', newline='') as f:
    f.readline()
    f.readline()
    reader = csv.reader(f, delimiter='\t')
    colors = list(reader)


# TTY colors
Colour = colors[REF_COLOR]

color = [(24, 24, 24)]  # Background
for c in Colour[1:]:
    color.append([int(x) for x in c.split(', ')])
color = np.asarray(color, dtype=np.float32)

# plt.imshow([color/255])

# Convert to JCh
lrgb = srgb_to_lin_srgb(color/255)
color_jch = linear_srgb_to_oklch(lrgb)

# Normalize lightness
color_jch[5,0] = (color_jch[2,0] + color_jch[5,0]) / 2  # adjust blue
color_jch[13,0] = (color_jch[10,0] + color_jch[13,0]) / 2  # adjust bright blue

j_mean = (np.mean(color_jch[2:8,0]) + np.mean(color_jch[10:16,0])) / 2
color_jch[2:8,0] = (color_jch[2:8,0] + j_mean) / 2  # color

# j_mean = np.mean(color_jch[10:16,0])
color_jch[10:16,0] = (color_jch[10:16,0] + j_mean) / 2  # bright color

color_jch[8,0] = (color_jch[8,0] + np.max(color_jch[2:8,0])) / 2  # white
color_jch[16,0] = (color_jch[16,0] + np.max(color_jch[10:16,0])) / 2  # bright white

# Normalize chroma
c_min = np.min([color_jch[2:8,1], color_jch[10:16,1]])
color_jch[2:8,1] = (color_jch[2:8,1] + c_min) / 2

c_min = np.min(color_jch[10:16,1])
color_jch[10:16,1] = (color_jch[10:16,1] + c_min) / 2

# Set hue(avg delta to original is about 26)
color_jch[2:8,2] = (0, 120, 60, 240, 300, 180)
color_jch[2:8,2] += 15

color_jch[10:16,2] = (0, 120, 60, 240, 300, 180)
color_jch[10:16,2] += 30

# Convert back to RGB
color_rgb = oklch_to_linear_srgb(color_jch)
color_rgb[8,:] = np.mean(color_rgb[8,:])
color_rgb[16,:] = np.mean(color_rgb[16,:])
color_rgb = gamut_clip_adaptive_L0_0_5(color_rgb)
color_rgb = lin_srgb_to_srgb(color_rgb)
rgbs = (color_rgb*255).round().clip(0, 255).astype('uint8')
rgbs[9,:] = 85

plt.figure()
plt.imshow([rgbs[0:9], rgbs[8:17]])


# Write putty.reg
putty = np.zeros([22, 3])
for pdx, rdx in enumerate([8, 16, 0, 9, 0, 11, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15, 8, 16]):
    putty[pdx] = rgbs[rdx]

REG_HEADER = '''Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\Default%20Settings]
'''
with open('putty-dof.reg', 'wt') as f:
    f.write(REG_HEADER)
    for idx, rgb in enumerate(putty):
        print('"Colour{}"="'.format(idx), end='', file=f)
        print(','.join(np.char.mod('%d', rgb)), end='', file=f)
        print('"', file=f)

# Write mintty
mintty = OrderedDict()
mintty['ForegroundColour'] = rgbs[8]
mintty['BackgroundColour'] = rgbs[0]
mintty['CursorColour'] = rgbs[11]
mintty['Black'] = rgbs[1]
mintty['BoldBlack'] = rgbs[9]
mintty['Red'] = rgbs[2]
mintty['BoldRed'] = rgbs[10]
mintty['Green'] = rgbs[3]
mintty['BoldGreen'] = rgbs[11]
mintty['Yellow'] = rgbs[4]
mintty['BoldYellow'] = rgbs[12]
mintty['Blue'] = rgbs[5]
mintty['BoldBlue'] = rgbs[13]
mintty['Magenta'] = rgbs[6]
mintty['BoldMagenta'] = rgbs[14]
mintty['Cyan'] = rgbs[7]
mintty['BoldCyan'] = rgbs[15]
mintty['White'] = rgbs[8]
mintty['BoldWhite'] = rgbs[16]

with open('mintty-dof', 'wt') as f:
    for key, rgb in mintty.items():
        print('{} = '.format(key), end='', file=f)
        print(','.join(np.char.mod('%d', rgb)), file=f)

# Print Windows Terminal JSON
WINTERM_KEYS = [
    'background',
    'black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white',
    'brightBlack', 'brightRed', 'brightGreen', 'brightYellow', 'brightBlue', 'brightPurple', 'brightCyan', 'brightWhite',
]

winterm_dict = {'name': 'DOF', 'selectionBackground': '#FFFFFF'}
for idx, key in enumerate(WINTERM_KEYS):
    r, g, b = rgbs[idx]
    winterm_dict[key] = f'#{r:02X}{g:02X}{b:02X}'

winterm_dict['foreground'] = winterm_dict['white']
winterm_dict['cursorColor'] = winterm_dict['brightGreen']

with open('winterm-dof.json', 'w') as jf:
    json.dump(winterm_dict, jf, indent=4)


# Generate preveiw
h = OrderedDict()
for key, rgb in mintty.items():
    h[key] = ''.join(np.char.mod('%02x', rgb))

d = OrderedDict()
d['"color:white; background-color:black"'] = '"color:#{}; background-color:#{}"'.format(h['ForegroundColour'], h['BackgroundColour'])
d['background-color:black;'] = 'background-color:#{};'.format(h['Black'])
d['background-color:red;'] = 'background-color:#{};'.format(h['Red'])
d['background-color:lime;'] = 'background-color:#{};'.format(h['Green'])
d['background-color:yellow;'] = 'background-color:#{};'.format(h['Yellow'])
d['background-color:#3333FF;'] = 'background-color:#{};'.format(h['Blue'])
d['background-color:fuchsia;'] = 'background-color:#{};'.format(h['Magenta'])
d['background-color:aqua;'] = 'background-color:#{};'.format(h['Cyan'])
d['background-color:white;'] = 'background-color:#{};'.format(h['White'])
d['font-weight:bold;color:dimgray;'] = 'font-weight:bold;color:#{};'.format(h['BoldBlack'])
d['font-weight:bold;color:red;'] = 'font-weight:bold;color:#{};'.format(h['BoldRed'])
d['font-weight:bold;color:lime;'] = 'font-weight:bold;color:#{};'.format(h['BoldGreen'])
d['font-weight:bold;color:yellow;'] = 'font-weight:bold;color:#{};'.format(h['BoldYellow'])
d['font-weight:bold;color:#3333FF;'] = 'font-weight:bold;color:#{};'.format(h['BoldBlue'])
d['font-weight:bold;color:fuchsia;'] = 'font-weight:bold;color:#{};'.format(h['BoldMagenta'])
d['font-weight:bold;color:aqua;'] = 'font-weight:bold;color:#{};'.format(h['BoldCyan'])
d['font-weight:bold;color:white;'] = 'font-weight:bold;color:#{};'.format(h['BoldWhite'])
d['color:dimgray;'] = 'color:#{};'.format(h['Black'])
d['color:red;'] = 'color:#{};'.format(h['Red'])
d['color:lime;'] = 'color:#{};'.format(h['Green'])
d['color:yellow;'] = 'color:#{};'.format(h['Yellow'])
d['color:#3333FF;'] = 'color:#{};'.format(h['Blue'])
d['color:fuchsia;'] = 'color:#{};'.format(h['Magenta'])
d['color:aqua;'] = 'color:#{};'.format(h['Cyan'])
d['color:white;'] = 'color:#{};'.format(h['White'])
d['"font-weight:bold;"'] = '"font-weight:bold;color:#{};"'.format(h['BoldWhite'])
d['"font-weight:bold;background-color:'] = '"font-weight:bold;color:#{};background-color:'.format(h['BoldWhite'])

with open(r'.tty-template.html') as f:
    html = f.read()

for k, v in d.items():
    html = html.replace(k, v)

with open(r'tty-preview.html', 'wt') as f:
    f.write(html)

# html = html.replace('font-weight:bold;', '')
# with open(r'tty-preview-nobold.html', 'wt') as f:
#     f.write(html)
