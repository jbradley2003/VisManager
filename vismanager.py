#!/usr/bin/env python3
"""
Image Reviewer
--------------
Browse images across subdirectories, mark each as Keep or Delete, then
batch-convert the keepers to PDF and remove the rest.

Supports TGA, PNG, JPEG, BMP, GIF, WebP, TIFF, ICO, DDS and PDF.  Which
types appear is toggled in the sidebar; deletion is controlled per type
in the Process dialog.  PDF preview needs pypdfium2 or PyMuPDF installed
(files without a preview are still fully reviewable).

Every keyboard shortcut is user-configurable via the "⌨ Shortcuts" button
in the toolbar.  Settings persist to ~/.vismanager.json.
"""

import os
import sys
import json
import math
import queue
import threading
from collections import OrderedDict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk

# Optional 3D cube support. Kept optional because VTK is a ~500 MB dependency;
# without it VisManager behaves exactly as before, minus .cube files.
try:
    import cube_viewer
    CUBE_SUPPORT = cube_viewer.VTK_AVAILABLE
except Exception:
    cube_viewer = None
    CUBE_SUPPORT = False

# ─── Branding assets (embedded) ───────────────────────────────────────────────
# Base64-embedded so PyInstaller has no data files to lose. A packaged build
# is therefore never missing its icon or wordmark.
import base64

LOGO_PNG_B64 = (
    "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"
)

LOGO_SMALL_PNG_B64 = (
    "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"
    "gg=="
)

WORDMARK_PNG_B64 = (
    "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"
)

ICON_B64 = {
    "file-single": (
        "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAD2ElEQVR42nVVTWhiVxj97nsqecNgOiU6MPlhkjji"
        "xtbWhTODkVQCJjSBjr4uBssECaFdhJAQ0GoHJgG7aDZqMuBk3JRkFWRIIi4CCdGxqDAZuhB3T0wXZjEEI6G++FN9"
        "XxftS/2ZnuXlct459zvfeQD/ghACEokEJBIJdEKn0zFut/tRMpl8xfP8hcPheAAAQNN0112gaRooimo7YxgGTCZT"
        "r9frnUin06FKpVLCFnAcdyyTyYAQAoQQ+CiUSiVltVrvhUKhZ7lc7gQ7UCgU3u/t7f14fX1dRERkWXYAALod2Wy2"
        "/kgk8rxYLOY6SbLZ7L7f739iNpvviEqi0egLQRCaiUTiJQB0uYNWgnK5/CEejwc8Hs9jrVbb03pvfHz8E5VKJR0b"
        "G+tFRBQEoWk0GuWEkPa3jMfjgUajUeM47nh0dFQqnsvlcsKy7MDOzs4PhULhPSJiLpc7AQA4PT3dFgShGQ6HV7qG"
        "Y7FY+gRBaNbrdV6r1fZoNBrZ4eHhz+Vy+UOr+kwm82ZpaekLmqZhdnZ2FBGxWq1eqdVqGSHkP+sURUEqlXqNiLi1"
        "tfXd4uLi54iIlUqlFIvFfE6n09Bpn6IoODs7+w0RMRAIWLtU2u32+4iIPM9f6PX6W5OTk31DQ0Nt4zMYDLfX1ta+"
        "ikajLzQajWxhYeEzRMRisZhTKBTUjUpCCDAMA/l8/i0ios/n+wYAQCqVwvT09N1gMPi0M0bz8/MahmGgVCr9gYjo"
        "crke3kRIzJHL5XqIiHh5eZnv7++nxWdoDXMwGHw6NTWlEFVvbGywiIj5fP4twzD/hJyiKCCEgEKhoMQsLi8vf7m5"
        "ufntu3fvfl1dXR03GAy3W+0PDw9LBgcHaZVKJa3Van8iItrt9vtt6wcAEAgErKKazsBqtdoep9NpiMVivkajUatW"
        "q1c0TcPu7u4SImIqlXrdNmlCCKjValm1Wr0Sv8gwDKyvr3+dyWTetNrnef4iHA6vSCQS0Ov1t+r1Oi8IQtNisfR1"
        "qQyHwyuCIDSPjo5+sVgsfSLJ+fn579vb29+zLDsgl8tvGmFkZETKcdxxo9GoxePxQBshIQSMRqNcEIRms9n8a2Zm"
        "5u7c3Jx6YmLi0077Ho/ncSwW8/E8f9GqHjoDCwCQSCReCoLQ3N/fd4tdaTab7/j9/ifZbHa/s0SKxWIuEok8t9ls"
        "/W2EYoRYlh0Qt+Xg4OAncZdbkcvlTkKh0DOr1XpPqVRSH+1EsTBlMhlwHHfcSlCpVErpdDrk9XonTCZTL8MwXe7+"
        "t8EBABwOxwOe5y+SyeQrt9v9SKfTMZ13xV9Ga2v/DQXzflftm0k/AAAAAElFTkSuQmCC"
    ),
    "files-stack": (
        "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAEAUlEQVR42o1Ub0jidxj/+tP0zDzd7Sb7zdwV10Zq"
        "rRGdzYSfEHa5hJKIiBjOFk2IcojC9Qe6waX24nzX4rpa0L2Q0JJxGBrMEYQuZqySRLZ0rMsw6Z8RmWXt2ZsZ7s5u"
        "+7z6vni+Hz7P83yeD0JZwDAMkclk9Dr4fD5Np9NV+ny+58lk8kCpVOIIoZy1OVFQUEAiCII1MjLyeTAYfAn/4PDw"
        "8I/z8/OTQCAwR6FQEIZhiEQi5SYhkUiorKzsltVq7dnb2/stQxIKheZNJtNDuVx+F8dxTKvVVgAAqNXqEoQQolAo"
        "Nyvr6en5BAAgHA7/pNfrq0QiEYMgCNbAwEDN+vq6/ejo6E8cx7FIJLK4s7PzK51Ov1klhmGIyWSS4vF40O/3v+By"
        "ueRYLLYOAJBMJg9sNpuupaWlECGE2traPgQAMBgMD/5TZWdn58cAAMPDw7LBwUEJQRCse/fuUWQy2Z2xsbG27e3t"
        "X4RCIc3v979IJBKv2Gw2CcOwN4lKS0upa2trNolEcnt1dXUmFoutU6lUZLPZdJl5bm1t/WyxWBoRQkgqlbIBAIxG"
        "Y11OZcXFxRQAAI/H81ShUHAAACwWS+Pk5OSXer2+SiAQ0EpKSvLa29uL3G63USwWM10u15Ozs7OjwsLC3P7p7+8X"
        "AwDI5fK7Ho/n6cnJyS5CCGk0GkG2fbxe7zMej0eurKzMv7y8PLdarT3Xbsk8qqqqGLu7u6mVlZW1aDS6ptfrexcX"
        "F49GR0dbmUwmi8FgsOx2uy0cDh9wOJx8pVJZ39jYaMBx/FMA+AvDsH+rBACYnp7+WqVS3QcAaG1t5c3OzhrS6fRZ"
        "TU0NU6VS3Xc4HI9SqdRxRunGxsYPJpPpoUgkYrzR7szMzDcAABKJ5HYwGHwZiUQWxWIxE7JwdXWVdrlcTzo6Oj7i"
        "cDjYW8+Ny+WSU6nU8fz8/LdNTU3vAwD09vZWaLXaivHx8S+kUik7u14oFNKGhoYIp9P5uKioKLcRjUZjHQCATCa7"
        "s7S09F1mKQghRKPRkEKh4ExNTX0Vj8eDGdX7+/u/CwQCWs5LYbPZpOPj46jP53teV1f3LgCA0+l8vLCwYMpuPRQK"
        "zZvN5vrq6uqCvLy83C1nzsdgMDwAAGhubv7A4XA8AgBIp9Nnbrfb2NXVVYrj+PXsqFTqdbDkTBsMwxCdTkfRaHRl"
        "c3PzRx6PR66trX0n+wOfz6f19fV9try8/D0AgEajEdy4mIxKtVpdAgDQ3d1dhhBCDQ0N701MTKgyYQEAkEgkXtnt"
        "dn15efmtt2YihmGIQqGgQCAwd3FxcXp6erqXIQkEAnNms7meIAhWfn7+/0vrTKwrlUo8mUweeL3eZzqdrpLP59Ny"
        "1b6eNH8DzGwdt9ljsRoAAAAASUVORK5CYII="
    ),
    "flag": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACYUlEQVR42qVTTUsbURQ9782bDCiIJBrsH4g7d+o/"
        "yMaNq9JSSqFCV1mWlG66cSkUCtaIWKmLrioidTFQQggkgggKLkKnEpoBmUUIGLCkGp37bjeZ6ctHu+nZzZt7z7nv"
        "nXMBA/Pz8+Pb29vPms1mjXuo1Wpf8vn84uTkpIjqpJSwLAtDSCaTYn19/WHUHATBWblcfnd8fPzh5uamzczs+/5R"
        "Lpebm5mZkVGf4zgwBeB5nsvMXK1WC9lsNuU4TvwvnU7LfD6/2G63/Ujo5OTko+u6q77vHwVBcBYXMzOXSqW35pRS"
        "SgjxR2xqakrmcrm5SqXyvtPptNhAXERE93t7ey8BIJFI9BEIIYbeY2JiQqRSKXF4ePhGa00AoHrqyrZtRwgBIoIp"
        "wswgophQa43r62sGgDAM74QQEgCk0aBNgkEwM8IwhNYaSikIISCM0dWopl5RTDAoMOqsj8iyLEgph65nWRaYGVrr"
        "v06sTOeICESEZDIppqen7TAMOQiC+9vb2z5C04zYZUNVLS0tpYvF4lqz2fzleV63Xq/fXV5efi8UCo9nZ2cTRASt"
        "NYgoFh+8M3e73Z9RLqrVamFzc/PJ7u7ui4uLi6/R+cbGxqOFhYXxsbExAMDBwcFrIrrvy1EYht2dnZ3nmUwmMRjM"
        "5eXlB6enp58iwqurqx+NRqMyFEhmZtd1V81mpRSUUn1OZrPZ1NbW1tPz8/PPjUajUiwW11ZWVjJ9RPv7+6+klLBt"
        "e+ghR276KNeYWUsppdZ6pCNRsqP9i+Jhfqve2FIplfiXYrQqJsxcSQBotVqe7/vf8B/4DdmKicFiIl5AAAAAAElF"
        "TkSuQmCC"
    ),
    "corners": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAABhUlEQVR42s1UMYrrMBScJ8kgJxBc5xJL0voOv80t"
        "fA8fJe0/wf52C+cGKdY47TcfEgksa36RaHGWJAtLip1SvBlGw7yHqqpe+r5/5wTjOA5lWS4AQGsNrTUAoCzLxTiO"
        "w3S27/v3qqpeTF3Xr9ba4nA47EhGktF7/885FwCAJBKcc2G/3/+x1i5ERImIWi6Xq7quX0GSXdc1RVGItRZ5nkNE"
        "cA8igjzPYa1FURTSdV1Dkia5OB6PHIbhijB1M31zzgEAxnFk4qtk0RgDEYFS6qZI+uZ05sI58wEgxhhCCB/Dt0Sm"
        "YgkhBMQYAwBIWZaL0+k07HY7d8/JvaxIYrVa5bPZLMOzIFprkESM8VsCKS+Fn4bnhU2Sbdu+ZVkGEXnY6qmIiCDL"
        "MrRt+0aS6hKYMcZcDX0lAgDGGCh17uLHioQQrsr4aEXS+4UTSUaTKj6fz8V7TxGB9/7hilhrQRLWWkl8cc79vXVG"
        "NpvNr6ZpTkqdGxJjxHq9nm2329+fz4j3vsezDtt/RhtVgsOK7DQAAAAASUVORK5CYII="
    ),
    "flag": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACYUlEQVR42qVTTUsbURQ9782bDCiIJBrsH4g7d+o/"
        "yMaNq9JSSqFCV1mWlG66cSkUCtaIWKmLrioidTFQQggkgggKLkKnEpoBmUUIGLCkGp37bjeZ6ctHu+nZzZt7z7nv"
        "nXMBA/Pz8+Pb29vPms1mjXuo1Wpf8vn84uTkpIjqpJSwLAtDSCaTYn19/WHUHATBWblcfnd8fPzh5uamzczs+/5R"
        "Lpebm5mZkVGf4zgwBeB5nsvMXK1WC9lsNuU4TvwvnU7LfD6/2G63/Ujo5OTko+u6q77vHwVBcBYXMzOXSqW35pRS"
        "SgjxR2xqakrmcrm5SqXyvtPptNhAXERE93t7ey8BIJFI9BEIIYbeY2JiQqRSKXF4ePhGa00AoHrqyrZtRwgBIoIp"
        "wswgophQa43r62sGgDAM74QQEgCk0aBNgkEwM8IwhNYaSikIISCM0dWopl5RTDAoMOqsj8iyLEgph65nWRaYGVrr"
        "v06sTOeICESEZDIppqen7TAMOQiC+9vb2z5C04zYZUNVLS0tpYvF4lqz2fzleV63Xq/fXV5efi8UCo9nZ2cTRASt"
        "NYgoFh+8M3e73Z9RLqrVamFzc/PJ7u7ui4uLi6/R+cbGxqOFhYXxsbExAMDBwcFrIrrvy1EYht2dnZ3nmUwmMRjM"
        "5eXlB6enp58iwqurqx+NRqMyFEhmZtd1V81mpRSUUn1OZrPZ1NbW1tPz8/PPjUajUiwW11ZWVjJ9RPv7+6+klLBt"
        "e+ghR276KNeYWUsppdZ6pCNRsqP9i+Jhfqve2FIplfiXYrQqJsxcSQBotVqe7/vf8B/4DdmKicFiIl5AAAAAAElF"
        "TkSuQmCC"
    ),
    "fullscreen": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAABhUlEQVR42s1UMYrrMBScJ8kgJxBc5xJL0voOv80t"
        "fA8fJe0/wf52C+cGKdY47TcfEgksa36RaHGWJAtLip1SvBlGw7yHqqpe+r5/5wTjOA5lWS4AQGsNrTUAoCzLxTiO"
        "w3S27/v3qqpeTF3Xr9ba4nA47EhGktF7/885FwCAJBKcc2G/3/+x1i5ERImIWi6Xq7quX0GSXdc1RVGItRZ5nkNE"
        "cA8igjzPYa1FURTSdV1Dkia5OB6PHIbhijB1M31zzgEAxnFk4qtk0RgDEYFS6qZI+uZ05sI58wEgxhhCCB/Dt0Sm"
        "YgkhBMQYAwBIWZaL0+k07HY7d8/JvaxIYrVa5bPZLMOzIFprkESM8VsCKS+Fn4bnhU2Sbdu+ZVkGEXnY6qmIiCDL"
        "MrRt+0aS6hKYMcZcDX0lAgDGGCh17uLHioQQrsr4aEXS+4UTSUaTKj6fz8V7TxGB9/7hilhrQRLWWkl8cc79vXVG"
        "NpvNr6ZpTkqdGxJjxHq9nm2329+fz4j3vsezDtt/RhtVgsOK7DQAAAAASUVORK5CYII="
    ),
    "folder": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACNUlEQVR42r1Uv2uTURS978dHYtoOzcc3BByiFsSl"
        "kyUF4xRw6NQlQ5FCh1qoS5BMEjLaRTA45SPUQCxE6F9QoRlE0iQOnTo0II1QHUugpSRf3o/jUCNtoVGCeODC43Lv"
        "e+e8e94j+lfI5XKPtNYBrqFer/uxWIxzzolz/sd9mFKq1263P9ZqtfdCCGmM0eFwOLK2trZVqVSeraysbIZCITLG"
        "XGkEcDUHABsbG0+un7C9vf2i1+t1R7FhjP1eSyKiiYmJSSklSSmJiEhrTeVyeSudTr+pVquZ/f39JuecWWsBANZa"
        "u7e31240GmeMMQJwwahQKCwyxigUCpEQghzHIcdxqFgsLuEGWGtNIpGYFEKQEIL4L4oMAAVBQMYYUkqRUorW19c/"
        "RCIR5roud12Xe54nXNfliURikjHGZ2dnbxtjCMCFtCAIAiklzc3NTV3Wzjln/X7fWGsxzAOgWCw2pbXuz8zM3J2f"
        "n/9+cHBwTgDg+/7TnZ2dVxgTrVarzACg2+12pqen7+Tz+ceHh4ffhhc7yjdSSq61tplM5mUymXxOxhgFAJ1O5/M4"
        "hj4+Pv7SbDbfkVKqZ601xWJxaTi5oRVuimFNKpWKAsDq6up9Gj6PhYUF73LRqAiHw8QYo1KptDwYDM49z+MEAEdH"
        "R5/GkXVycvJ1d3f3NRGRPD09/eE4zq1CobAohJAA7Khmzrmw1pp4PP4gGo3e833/LWOMKJvNPgyC4GycsZdKpWUh"
        "xF/9Dv8fPwH5SKOgo5Hv9wAAAABJRU5ErkJggg=="
    ),
    "undo": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACw0lEQVR42pVUPUgbYRh+7i9KUmuiYDpoyVQTQh0l"
        "gorcEVqIh7qISDdREK9TWyx0KCjWrUOX1smhRIcoIqQJShEDZjl06KIQvRCaQUsHDTHNmTP3dmgvVatEn+X74f2e"
        "73l/AQALCwvK5ORkAAB4nsfw8LBndXX1TTabVUulUkHX9Vw6nU4sLi4+l2XZjb/gOA64eEilUuvlctmYmJh4nEwm"
        "P1EVrK2tvfP7/TWXyDweD5/P548uGuq6notEIi9GRkYeiaLokiSpYXx83B+NRt9aNicnJ98lSWqokIVCoSbTNMuG"
        "YRR1Xc8VCoWfPT09TtwAURRdqVRqnYjo9PT0h8/nqwEAzM7OPrkqPRaLTTmdTsZms4HneXAcV1kBoLm5mTs4ONgg"
        "IkokEh9YlgXm5uaeHR4efstkMsl0Op3Y29v7omnaZkdHR91/AQVgs9kAAF1dXfWGYRSJiPr6+h5AEAQ4HA7U1tZC"
        "EAQwDINq4HkeABCLxaZM0yyvrKy85gCgVCrh/PwcpmniNmBZFkQEh8NxJMuyUldX52IvPr6NGgAgIhARNE37AQBu"
        "t9vPzszMBOfn50fsdvudyK5jJyKiUCjUxDBMxf9qMWIYBmNjYz4iomw2q7Kqqs4bhvGrv7//KRHdRQAGBgaGichU"
        "VTUCRVHaiIjy+fxRa2urDQAEQbiRwEp/d3d3Jf2yLLtht9uxu7sbJSLa3t7+XF9fz1jyrSK8WpAtLS2cpmmbREQb"
        "GxvvWZb980tnZ+f9crlsEBHt7OyE29vbHTcpCgaDjfv7+18tL7xer41hmH+VOzQ09PDs7CxPRGQYRnFpaenl6Oio"
        "V5KkhmAw2KgoSls8Hp+2knN8fJwRRdF1qfqtTSAQuLe1tfWx2hiJx+PTVrNebaHKBcuyGBwcbFleXn6VyWSSuq7n"
        "isXisaZpm+FweKK3t/fawfYbAyy/Jf3bZwUAAAAASUVORK5CYII="
    ),
    "redo": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACtklEQVR42o1UPUgbYRh+71+SUM8UjINap8Zr6iRY"
        "B+mhOaE0QdNJM0oggtd2KVW6iYWCYwdph24lOgSDQ3OilBKo0iBxFYke1hCkpRSVmHg/yb0d7KVNrDXP8j3wfe/D"
        "97x/AL9BUZRNYXR0tG1paenJwcHBZ13XC4ZhFHO5XHplZeVFOBy+RdM0AABMT0/fW1xcfAz1Ij6fj1tbW3uF12Bj"
        "Y+ONLMs95XJZz2az6xRF/RGRJMl9cnKSsx8nk8nZqampu5IkuQcHB1sikcjteDz+TNO0079Fz87Ovnd1dV18URAE"
        "rlAofENEzGaz636/3w1XQBRFvlgs/tA07dQ0zXPLsirBYNADJElCKpV6jYi4v7//qb29nbLt0jRdPVmWBZ7nCUVR"
        "5uqtzs/PP6SDwWCbKIpPy+WyNjEx8Sifz1dYlgXDMGpyaBgG9Pb2urxe7/3d3V2F4zgXSZI0x3EunufdkEgkZizL"
        "qiSTyVkAALsi/wNBEMAwDDQ1NYHT6QSGYQDy+XwGETEajQoEQTQkVA+SJIH0eDw+AABVVb8jIiBiQ8EEQVS5ZVlA"
        "/+uiURGHwwELCwuRo6OjXNXa5OTknUat0TQNBEFAIBBotStHbm1txRHRCoVC4UZtAQAgIoRCoQemaZbS6fQ7GBkZ"
        "aUNENE3zXBRFHgCAZdkrBRiGAQAAr9fL2k0sy3JPTUOqqprq6Oi41JA2t203NzcTmUzmPSLizs7OB4fDcZG47u7u"
        "qvre3t5HSZKuHJG+vj7n9vZ2DBGxUqmYAwMDN2omf2hoqOX4+PirnTxFUeZkWe4ZHh6+6ff73dFoVFheXn5umuY5"
        "IqKu64Xx8fHOmhVkE0EQuNXV1ZfXrZHNzc23/f39rvo9dmmxBQKB1lgsJquqmiqVSj81TTs9PDz8kkgkZsbGxjpJ"
        "krwU8wvih7QZgZWx2QAAAABJRU5ErkJggg=="
    ),
    "keyboard": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACTklEQVR42t2TMUscQRTH38yOx9ysd+c6661zJzkE"
        "lSBizm6NNkaQg1SpzFWpDvwK53UWglZW2tjlY9hcYwLhgpAi2ggrwrpsCnU3Odxjd16KoJCAgUAqf+0r3vvz/z2A"
        "p02n01kKw/AU/5EwDE87nc4SAABpt9uL29vbHwAAwjD8mmXZgFLKtNYpIYTeLyOEUK11ej8zDCNXLpdnAQA2Nzdf"
        "QhRFfpIkcaPRsAEAGGOPXk4IAQCAoaEhAABYW1uTg8HgRxRFPiAiXl5efsrn87C/v/+2Vquxra2tV67rDrdarefN"
        "ZrO2uro62m63F2dmZnJ7e3tvHMehBwcHTcdxqOd5x4iIDBE1AEChUKC2bSvOOZVSjpmmmSuVSgVKKe33+4llWaNC"
        "CMO27XHOObVtu1IqlRgAACJqQET0ff+Ecw7VatWglIJSinLOQUpJRkZGiGma4DgOZYzBxMSEQQiBarVqCCHA9/0T"
        "RERARLy4uPiolKJRFPmu6w73er336+vrzw4PD9/t7u6+3tjYmD06OtpZXl4uep53PDc3x+M4Dur1ev78/LyLiEi0"
        "1lkQBF+mp6cXLMsygiDI5ufnxd3dXSaEYFmW6TRN0TRNdn19PbAsK9fr9b4rpYybmxt9dnb2WSn14iEapb+anpyc"
        "ZEmSxH/zx3XdYQAASulDNBbH8ZWUcqrRaIx1u91vt7e3WavVqpumyf+sHxExTdPM87y+EAJWVlbKUsqpOI6vfhPS"
        "9/0TrXUaRVGgtc4ecYkUi8VxwzBylUpl4UHI//UiT5if9riSEBIa18YAAAAASUVORK5CYII="
    ),
    "flip-vertical": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACH0lEQVR42s1TMWtTURg99973YjQEippoIKGFQCCB"
        "QIc+HR3SIQQSdHNx7g+IiZsZ+pZCIVnMkKmgoEKIQ0smIZAOQgh0yCC+rWIVkoeQ0Ch9j3s/l7xHhBZpdfBs93K/"
        "w7nnOwf4VxBCAAAajcajw8PDF5FIhC/fX/QeANbW1rSDg4OabdsWAGBnZ6dACwwGgz2PjDHmD3HOwTkHAOi6jmq1"
        "et9xnLk3h2az+dg7uK77k4jo6OjoTSwW44wxcM6haZpPWCwW7xwfH38gIqrX6w9N09wkIgIRkeM48+l0+kUpJcfj"
        "8Ucionw+f3tZVTqdvtbpdJ4REfV6vfr6+vp1ANja2soQEcEwjNDGxkZoOBy+VErJQqEQyeVyN3VdB+ccKysrrFar"
        "PZjNZl+JiLa3t3Orq6taPB4XqVQqYJrmplJK+pJHo9E7IqJsNhsEgEAgAABotVpPaAlSSpfOgSaEwOKLakHAhRBQ"
        "SgEAdnd333a73feMMSaE4EIIrpRSni2MMTaZTE41KeVv6yUiSCn9NVuW5ViW9e1PMfIVeWCMQQjhm5xKpQKZTOYW"
        "Y4xxztl5JLZtzy/t0UXQDMMIERHOzs5OiUglEolwNBq90e/3v3POUa1WX52cnHwul8uvw+FwzHXdH4uAakth1S6V"
        "o3a7/XQ5vEopeeVkl0qlu54Ny3G4UteCwSAqlcq9yWTyyVf0N+1PJpP6/v7+c7/9/xV+AVFDv+aDJdlTAAAAAElF"
        "TkSuQmCC"
    ),
    "flip-horizontal": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACu0lEQVR42pVUQUsbURCe3fd202ygkcQQtSYXw/4A"
        "DaGXNAUhSMglMaL+BC9RCXhUWk9BFD00OQi5ePHUnnsreCiBQPAoiGAvIUiDpZvEZPft10u3bDQK/S4D84ZvvvmG"
        "eURExBgjIqJqtbpuGEY7kUj43HknJhIJn2EY7Wq1uu7Oj6BcLmcAwDCMdjwe99EYxONxn2EYbQAol8sZ95tERHR8"
        "fJzb3Nz8LIQY9nq9n9fX1984557HRJZlDWKx2HtN04KMMfXk5CS/tbX15V9BvV6vAYBpmn3btgVegG3bwjTNPgDU"
        "6/XaSKdwOCw3Go0zAGi1WpfZbDY8Pz+vLSwsaO6YzWbDrVbrEgAajcbZ1NSU/GT+UCgkN5vNcwBIJpP+cR4lk0k/"
        "ADSbzfNQKPSUxHE/EAhI6XQ6qCgKqapKnHNijBHnnFRVJUVRKJ1OB4PBoPTs1iRJov/Bi/WyLBPnnLxeL1UqlTVd"
        "11UiIl3X1UqlsqZpGnHOSZbll7s4Und3d98BwMrKyiwRUaFQmAWAvb291LMjudVIkkRzc3NKt9u9M02zn8vlZoiI"
        "crncjGma/W63exeLxRRJkp6okt0zA6Cjo6Mdr9cbYIypjDH5bxOJc/5K07TJw8PDHQDjPXKkLi0tTQLA/v7+omVZ"
        "g9XV1SgR0fLy8hsAGAwGvwEgk8mExo7orPj29vb7xcXFp3A4LANAoVCYfUxk27a4urr66vF4RohkIiIhBG1vbyei"
        "0ejbjY2NEudcemYZqhBiqOt6ulgsJoQQowXT09Pyw8PDr4ODg6xzMm5F+Xx+BgAsyxrYti2EEOb9/f2PSCTCRhTV"
        "arUPHo/ndb/f75VKpXixWFx0TCYi4pwz11JkIiK/3x85PT39OKKo0+ncPL764XDYTaVSE0REqVRqYjgcdoUQpvMD"
        "2LYtOp3OjcPxB7dgdESjahvsAAAAAElFTkSuQmCC"
    ),
    "expand": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAABkUlEQVR42q1TTWqsQBAu24Fpko2TlZv2Dp5AabxE"
        "bjCzTm5kkyx0kV3IJRTBhUL2LoIkG7UFp7+36jzJzMB7ZD5o6C6+qq6vfqgoiicAMMYcjTFHAEjTdE9ExBgjC3tX"
        "Sh1+8ouieNqEYXhvyVrrL8dxGOf8li5gu93eaK2/ABjOuUdEFIbhPdmoANB1XSWl3BERua57EsTapJS7rusq62eM"
        "OdKyLPMwDB99378DQFVVWRAEm0vSgiDYVFWVAUDf9+/DMHwsyzKTjRpFkVfX9QsAtG37JoRwHceh9RFCuG3bvgFA"
        "XdcvcRx71p/SNN3nef5IRCSEcJumeQWAJEnurBwrKUmSOwBomuZVCOESEeV5/qiUOpyk7vs+s3U6Bynlzvd99lM6"
        "Mca+DY7j0L/Cctf+J4RzHVt37tyHjK6Fq0v7dbGVUofftj9N0/33QMZx/N8DGUXR34G82opcbWnXj3Ec+2maPrMs"
        "e7iUUZZlD9M0fY7j2K+TYGVZPlsy59zjnHvzPI+Xuqa1HizP2sqyfP4DV0mIUPnlzvkAAAAASUVORK5CYII="
    ),
    "edit-document": (
        "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAcUlEQVR4nO2USw6AMBBCwfT+V8aNGj+TCq1L2Za8"
        "lA4d4GMRACSpayIZUXtAbXJZi2MiSRdqAROoBTzHtm6avNGbtyVmZ9oXYFyPQvZQXP2RxyNL0nE+28NH6WeA5Q8a"
        "BVawVhld8L4wptsRLYoUetcKHvCDzN81x04AAAAASUVORK5CYII="
    ),
    "collapse": (
        "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACCElEQVR42s2UP2/aUBTFz/tjYVWISoAHpGR5A7Cx"
        "VBliFoIUGakj5ZuwuHwW2DOlViOUDhAWlKUSg5HtASExRx4qBKE2vp1AlKBmYehvfede3Xfuewe+7/dns9mTUkoD"
        "gGq1mmm321e6rgMAGGNgjAEAdF1Hu92+Mk0zAwBKKW02mz35vt/HYrF4JiLyPO+hUChwx3E6RESWZeUBQEoJIQQA"
        "wLKsPBGR4zidQqHAPc97ICJaLBbPUEppQRA8EhG5rnvvuu59HMebVqt1uWskpQQAtFqtyziONzsdEVEQBI+72yCX"
        "y7HJZHJHBzSbzYvjRs1m8+JQM5lM7nK5HAMAbppmptfrfRVCaFEUrdbrdZgkSSyl5DhCSsmTJInX63UYRdFKCKF1"
        "u13bNM0MbNu+phPU6/UsAAgh9h7V6/XsKa1t29cslUqhVqvl0+m0vttSGIarwWAQEtFfEzHGcHNzk81msx92Z8vl"
        "8nU4HL7gXDDGGDjn+7cCAESE7XZ7skAI8UabJAk4/jfOZ/a51i9Ho5HrOE5HKfWpVCrdxnH8mkqlMoZhpAGEh8Ya"
        "hpFOkiTebDa/pJR6EAQ/5vP5z9Fo5J7ti0illNbv978Xi8Xb6XT6DQDK5XKDc86ODeWcs+12+9v3/T4AVCqVL+Px"
        "+GOj0fj8bowIIfYT/TNGjoPNNM13g61arb4Jtj/VBblGlfAo1AAAAABJRU5ErkJggg=="
    ),
}


_ICON_CACHE = {}


def icon(name):
    """
    Decode an embedded icon once and reuse the PhotoImage.

    A PhotoImage belongs to the Tk interpreter that created it, so a cached
    one goes stale the moment its root is destroyed. The cached entry is
    probed before reuse and rebuilt if the old interpreter has gone away.
    """
    name_key = (_interp_key(), name)
    cached = _ICON_CACHE.get(name_key)
    if cached is not None:
        try:
            cached.width()          # cheap liveness check
            return cached
        except Exception:
            _ICON_CACHE.pop(name_key, None)
    try:
        img = tk.PhotoImage(data=base64.b64decode(ICON_B64[name]))
    except Exception:
        img = None
    _ICON_CACHE[name_key] = img
    return img


APP_NAME = "VisManager"
APP_TAGLINE = "Review, convert, clean up"


def _photo_from_b64(b64):
    """Decode an embedded PNG into a Tk PhotoImage. Returns None on failure."""
    try:
        return tk.PhotoImage(data=base64.b64decode(b64))
    except Exception:
        return None


# ─── Glyphs (BMP-only) ────────────────────────────────────────────────────────
# Every symbol here lives in the Basic Multilingual Plane (<= U+FFFF).
# Astral-plane emoji such as U+1F4C2 folder or U+1F501 repeat are rendered as
# empty boxes or surrogate garbage by Tk 8.6 on Windows, so they are avoided
# entirely. ASCII_GLYPHS is a last-resort fallback probed at startup.
GLYPHS = {
    "open":     "\u25a4",   # ▤ lined rectangle, stands in for a folder
    "process":  "\u2699",   # ⚙ gear
    "keys":     "\u2328",   # ⌨ keyboard
    "keep":     "\u2713",   # ✓ check
    "delete":   "\u2717",   # ✗ ballot X
    "invert":   "\u27f3",   # ⟳ clockwise open circle arrow
    "prev2":    "\u25c0\u25c0",
    "prev":     "\u25c0",
    "next":     "\u25b6",
    "next2":    "\u25b6\u25b6",
    "cont":     "\u21c9",   # ⇉ rightwards paired arrows
    "wrap":     "\u21bb",   # ↻ clockwise open circle arrow
    "checked":  "\u2611",   # ☑
    "unchecked": "\u2610",  # ☐
    "warn":     "\u26a0",   # ⚠
    "dot":      "\u25c9",   # ◉
    "dot_o":    "\u25ce",   # ◎
    "clear":    "\u2715",   # ✕
    "rot_ccw":  "\u27f2",   # ⟲ anticlockwise
    "rot_cw":   "\u27f3",   # ⟳ clockwise
    "flip_h":   "\u21c4",   # ⇄ horizontal
    "flip_v":   "\u21c5",   # ⇅ vertical
    "fullscreen": "\u26f6", # ⛶ fullscreen
    "help":     "?",
    "flag_on":  "\u2691",   # ⚑ flagged
    "flag_off": "\u2690",   # ⚐ not flagged
    "note":     "\u270e",   # ✎ pencil
    "export":   "\u21e9",   # ⇩ export
}

ASCII_GLYPHS = {
    "open": "[+]", "process": "[>]", "keys": "[K]", "keep": "OK",
    "delete": "X", "invert": "~", "prev2": "<<", "prev": "<",
    "next": ">", "next2": ">>", "cont": "->", "wrap": "<->",
    "checked": "[x]", "unchecked": "[ ]", "warn": "!", "dot": "*",
    "dot_o": "o", "clear": "x",
    "flag_on": "[F]", "flag_off": "[ ]", "note": "N", "export": "v",
    "rot_ccw": "<|", "rot_cw": "|>", "flip_h": "<>", "flip_v": "^v",
    "fullscreen": "[ ]", "help": "?",
}


def probe_glyphs(root):
    """
    Verify Tk can actually render the symbol set; fall back to ASCII if not.
    A font that lacks a glyph reports a zero-width bounding box, so measuring
    catches silent tofu before the user ever sees it.
    """
    global GLYPHS
    try:
        probe = tk.Label(root, text=GLYPHS["keep"] + GLYPHS["delete"] + GLYPHS["next"])
        probe.update_idletasks()
        w = probe.winfo_reqwidth()
        probe.destroy()
        if w < 8:
            GLYPHS = dict(ASCII_GLYPHS)
    except Exception:
        GLYPHS = dict(ASCII_GLYPHS)


# ─── Constants ───────────────────────────────────────────────────────────────
BG_DARK      = "#1e1e2e"
BG_MID       = "#2a2a3e"
BG_SIDEBAR   = "#252538"
TEXT_PRIMARY = "#e8e8f8"
TEXT_MUTED   = "#9090b8"
BORDER       = "#3a3a55"

# Toolbar / primary actions
ACCENT_BLUE  = "#4f8ef7"        # Open Directory label colour
BTN_OPEN     = "#1a5fd4"        # Open Directory button  — strong cobalt
BTN_OPEN_HOV = "#2272f0"
BTN_PROCESS  = "#6d28d9"        # Process Images         — vivid violet
BTN_PROCESS_HOV = "#7c3aed"

# Navigation buttons (was BG_MID — invisible)
BTN_NAV      = "#3a4e72"        # slate-blue, clearly visible on BG_MID
BTN_NAV_HOV  = "#4a6090"

# Keep / Delete — main action buttons
BTN_KEEP     = "#15803d"        # rich forest green
BTN_KEEP_HOV = "#16a34a"
BTN_KEEP_ACT = "#166534"        # pressed / active state

BTN_DEL      = "#b91c1c"        # clear crimson
BTN_DEL_HOV  = "#dc2626"
BTN_DEL_ACT  = "#991b1b"        # pressed / active state

# Sidebar quick-action buttons
BTN_KEEP_SB  = "#166534"        # darker green — legible on dark sidebar
BTN_DEL_SB   = "#991b1b"        # darker red
BTN_INVERT   = "#4b5563"        # neutral slate

# Canvas background tint
KEEP_BG      = "#0a2818"
DELETE_BG    = "#280a10"

# Shortcuts dialog
BTN_KEYS     = "#0e7490"        # teal — Shortcuts button
BTN_KEYS_HOV = "#0891b2"
CAPTURE_BG   = "#78350f"        # amber — "press a key" state

# Scrollbar thumb — deliberately bright so the moving part is obvious
# against the dark trough. The old thumb was BORDER (#3a3a55), which sat
# only a few shades off the trough and was nearly invisible.
THUMB        = "#6b8cff"        # idle  — clearly visible periwinkle
THUMB_HOVER  = "#8aa5ff"        # hover — brighter
THUMB_DRAG   = "#a9beff"        # dragging — brightest

# Flags / notes
FLAG_ON      = "#b45309"        # amber — flagged
FLAG_ON_HOV  = "#d97706"
FLAG_TEXT    = "#fbbf24"


# ─── Action registry ──────────────────────────────────────────────────────────
# (action_id, human label, default binding, handler attribute name)
ACTIONS = [
    ("keep",        "Mark as KEEP",          "<Key-k>",             "act_keep"),
    ("delete",      "Mark as DELETE",        "<Key-d>",             "act_delete"),
    ("toggle",      "Toggle Keep/Delete",    "<Key-space>",         "toggle_state"),
    ("next_image",  "Next image",            "<Key-Right>",         "next_image"),
    ("prev_image",  "Previous image",        "<Key-Left>",          "prev_image"),
    ("next_folder", "Next folder",           "<Control-Key-Right>", "next_folder"),
    ("prev_folder", "Previous folder",       "<Control-Key-Left>",  "prev_folder"),
    ("keep_all",    "Keep all in folder",    "<Control-Key-k>",     "keep_all_folder"),
    ("delete_all",  "Delete all in folder",  "<Control-Key-d>",     "delete_all_folder"),
    ("invert",      "Invert folder",         "<Control-Key-i>",     "invert_folder"),
    ("nav_mode",    "Toggle nav mode",       "<Key-w>",             "toggle_nav_mode"),
    ("preload",     "Toggle preload mode",   "<Key-p>",             "toggle_preload"),
    ("note",        "Add / edit note",       "<Key-n>",             "edit_note"),
    ("flag",        "Toggle flag",           "<Key-f>",             "toggle_flag"),
    ("export_notes", "Export notes to .txt", "<Control-Key-e>",     "export_notes"),
    ("rot_ccw",     "Rotate left",           "<Key-bracketleft>",   "rotate_ccw"),
    ("rot_cw",      "Rotate right",          "<Key-bracketright>",  "rotate_cw"),
    ("flip_h",      "Flip horizontal",       "<Key-h>",             "flip_horizontal"),
    ("flip_v",      "Flip vertical",         "<Key-v>",             "flip_vertical"),
    ("rot_reset",   "Reset orientation",     "<Key-r>",             "reset_transform"),
    ("fullscreen",  "Fullscreen image",      "<Key-F11>",           "toggle_fullscreen"),
    ("help",        "Help",                  "<Key-F1>",            "open_help"),
    ("cube_setup",  "Isosurface settings",   "<Key-i>",             "open_cube_settings"),
    ("cube_export", "Export 3D view",        "<Control-Key-3>",     "open_cube_export"),
    ("zoom_in",     "Zoom in",               "<Key-equal>",         "zoom_in"),
    ("zoom_out",    "Zoom out",              "<Key-minus>",         "zoom_out"),
    ("zoom_fit",    "Zoom to fit",           "<Key-0>",             "zoom_fit"),
    ("zoom_100",    "Zoom 100% (1:1)",       "<Key-9>",             "zoom_actual"),
    ("open_dir",    "Open directory",        "<Control-Key-o>",     "browse_directory"),
    ("process",     "Process images",        "<Control-Key-p>",     "process_images"),
]

DEFAULT_BINDINGS = {aid: default for aid, _lbl, default, _h in ACTIONS}
ACTION_LABELS    = {aid: lbl     for aid, lbl, _d, _h in ACTIONS}
ACTION_HANDLERS  = {aid: h       for aid, _l, _d, h in ACTIONS}

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".vismanager.json")
# Settings used to live here under the old app name; migrated on first run.
LEGACY_CONFIG_PATH = os.path.join(os.path.expanduser("~"),
                                  ".tga_reviewer_keys.json")

# Keysyms that are modifiers only — never a valid binding on their own
MODIFIER_KEYSYMS = {
    "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
    "Meta_L", "Meta_R", "Super_L", "Super_R", "Caps_Lock", "Num_Lock",
    "Scroll_Lock", "Mode_switch", "ISO_Level3_Shift",
}

# Pretty names for display
_KEY_DISPLAY = {
    "Left": "←", "Right": "→", "Up": "↑", "Down": "↓",
    "space": "Space", "Return": "Enter", "BackSpace": "Backspace",
    "Delete": "Del", "Escape": "Esc", "Prior": "PgUp", "Next": "PgDn",
    "Home": "Home", "End": "End", "Tab": "Tab", "period": ".",
    "comma": ",", "slash": "/", "backslash": "\\", "semicolon": ";",
    "minus": "-", "equal": "=", "bracketleft": "[", "bracketright": "]",
    "quoteright": "'", "grave": "`",
}
_MOD_DISPLAY = {
    "Control": "Ctrl", "Command": "Cmd", "Option": "Opt",
    "Alt": "Alt", "Shift": "Shift",
}


def rel(path, base):
    r = os.path.relpath(path, base)
    return "." if r == "" else r


def event_to_binding(event):
    """
    Convert a Tk KeyPress event into a canonical binding string
    like '<Control-Key-k>', '<Key-Left>' or '<Key-1>'.

    NOTE the mandatory 'Key-' prefix.  Without it Tk reads '<1>' as
    MOUSE BUTTON 1 rather than the digit key, so number shortcuts
    silently never fire.
    """
    keysym = event.keysym
    if keysym in MODIFIER_KEYSYMS:
        return None

    state = event.state
    mods = []
    # Modifier bit layout differs between macOS Aqua and X11/Windows
    if sys.platform == "darwin":
        if state & 0x10:  mods.append("Command")
        if state & 0x8:   mods.append("Option")
        if state & 0x4:   mods.append("Control")
    else:
        if state & 0x4:   mods.append("Control")
        if state & 0x20000: mods.append("Alt")   # Windows/X11 Alt (Mod1)

    # Normalise single letters to lowercase; Shift is implied by the
    # uppercase keysym so we only record it for non-alphabetic keys.
    if len(keysym) == 1 and keysym.isalpha():
        keysym = keysym.lower()
    elif state & 0x1 and len(keysym) > 1:
        mods.append("Shift")

    return "<" + "-".join(mods + ["Key", keysym]) + ">"


def split_binding(binding):
    """'<Control-Key-k>' → (['Control'], 'k').  Tolerates legacy '<k>' form."""
    inner = binding.strip("<>")
    parts = [p for p in inner.split("-") if p != ""]
    if "Key" in parts:
        i = parts.index("Key")
        return parts[:i], "-".join(parts[i + 1:]) or "-"
    # Legacy form written before the Key- prefix was introduced
    return parts[:-1], parts[-1]


def normalize_binding(binding):
    """Upgrade any legacy '<k>' / '<Control-1>' binding to the Key- form."""
    if not binding:
        return ""
    mods, key = split_binding(binding)
    return "<" + "-".join(mods + ["Key", key]) + ">"


# Some physical keys report different keysyms depending on Shift/numpad.
# Binding the aliases too means "-" works whether pressed on the main row or
# the number pad, and "+" works without having to hold Shift for "=".
KEY_ALIASES = {
    "equal":  ["plus", "KP_Add"],
    "minus":  ["underscore", "KP_Subtract"],
    "plus":   ["equal", "KP_Add"],
    "0":      ["KP_0"],
    "9":      ["KP_9"],
}


def binding_sequences(binding):
    """
    All Tk sequences to bind for a canonical binding.  For single letters
    we bind both cases so Shift/CapsLock don't break the shortcut.
    """
    if not binding:
        return []
    mods, key = split_binding(binding)
    seqs = ["<" + "-".join(mods + ["Key", key]) + ">"]
    if len(key) == 1 and key.isalpha():
        other = key.upper() if key.islower() else key.lower()
        seqs.append("<" + "-".join(mods + ["Key", other]) + ">")
    for alias in KEY_ALIASES.get(key, []):
        seqs.append("<" + "-".join(mods + ["Key", alias]) + ">")
    return seqs


def display_binding(binding):
    """'<Control-Key-k>' → 'Ctrl+K';  '<Key-Left>' → '←'."""
    if not binding:
        return "—"
    mods, key = split_binding(binding)
    key_txt = _KEY_DISPLAY.get(key, key.upper() if len(key) == 1 else key)
    return "+".join([_MOD_DISPLAY.get(m, m) for m in mods] + [key_txt])


DEFAULT_SETTINGS = {
    "nav_mode":      "continuous",   # "continuous" | "wrap"
    "fullscreen_mode": "screen",     # "screen" (whole display) | "window"
    "cube_export_format": "png",
    "cube_export_scale": 2,
    "cube_export_white": True,
    "cube_export_transparent": False,
    "preload_mode":  "lazy",         # "lazy" (one at a time) | "folder" (preload)
    "pdf_mode":      "per_image",    # "per_image" | "per_folder" | "combined"
    "delete_source": False,          # legacy global fallback
    "enabled_types": [t for t, _l, _e in ()],   # filled in below
    "delete_marked_types": {},       # {type_id: bool}
    "delete_source_types": {},       # {type_id: bool}
}


# ─── Supported file types ─────────────────────────────────────────────────────
# (type_id, display label, {extensions})
FILE_TYPES = [
    ("tga",  "TGA",  {".tga"}),
    ("png",  "PNG",  {".png"}),
    ("jpeg", "JPEG", {".jpg", ".jpeg", ".jpe"}),
    ("bmp",  "BMP",  {".bmp", ".dib"}),
    ("gif",  "GIF",  {".gif"}),
    ("webp", "WebP", {".webp"}),
    ("tiff", "TIFF", {".tif", ".tiff"}),
    ("ico",  "ICO",  {".ico"}),
    ("dds",  "DDS",  {".dds"}),
    ("pdf",  "PDF",  {".pdf"}),
    ("cube", "Cube", {".cube", ".cub"}),
]

TYPE_LABELS = {tid: lbl for tid, lbl, _e in FILE_TYPES}
TYPE_EXTS   = {tid: exts for tid, _l, exts in FILE_TYPES}
ALL_TYPE_IDS = [tid for tid, _l, _e in FILE_TYPES]
EXT_TO_TYPE = {e: tid for tid, _l, exts in FILE_TYPES for e in exts}
ALL_EXTS    = set(EXT_TO_TYPE)

# PDFs are already PDFs — they're never re-converted, only filtered/deleted.
NON_CONVERTIBLE = {"pdf", "cube"}

DEFAULT_SETTINGS["enabled_types"]       = list(ALL_TYPE_IDS)
DEFAULT_SETTINGS["delete_marked_types"] = {t: True  for t in ALL_TYPE_IDS}
DEFAULT_SETTINGS["delete_source_types"] = {t: False for t in ALL_TYPE_IDS}


def type_of(path):
    return EXT_TO_TYPE.get(os.path.splitext(path)[1].lower())


# ─── Orientation ──────────────────────────────────────────────────────────────
# Any run of 90-degree rotations and flips composes to a single element of the
# dihedral group D4 — a rotation plus an optional mirror. Keeping state as
# (rot, mirror) rather than a list of operations means it stays exact no matter
# how many transforms are chained, and it serialises to two values.
#
#   display = Rotate(rot quarter-turns clockwise) after Mirror(if mirror)
#
_ROT_TRANSPOSE = {1: Image.ROTATE_270,    # 90 clockwise
                  2: Image.ROTATE_180,
                  3: Image.ROTATE_90}     # 270 clockwise


def apply_transform(img, rot, mirror):
    """Return a new image with the stored orientation applied."""
    if img is None or (not rot and not mirror):
        return img
    if mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if rot:
        img = img.transpose(_ROT_TRANSPOSE[rot % 4])
    return img


def compose_transform(rot, mirror, op):
    """
    Fold one more operation into an existing (rot, mirror) state.

    The flip cases are not simply "toggle mirror": mirroring commutes with
    rotation only after negating the angle, so F(h) after R(n) equals
    R(-n) after F(h). Getting this wrong makes flips behave erratically
    once the image has been rotated.
    """
    if op == "cw":
        return (rot + 1) % 4, mirror
    if op == "ccw":
        return (rot - 1) % 4, mirror
    if op == "h":
        return (-rot) % 4, not mirror
    if op == "v":
        return (2 - rot) % 4, not mirror
    return 0, False        # "reset"


def transform_label(rot, mirror):
    if not rot and not mirror:
        return ""
    parts = []
    if rot:
        parts.append(f"{rot * 90}\u00b0")
    if mirror:
        parts.append(GLYPHS["flip_h"])
    return " ".join(parts)


# ─── PDF rendering (optional backends) ────────────────────────────────────────
# Backends are tried best-first.  The last one, pypdf, is PURE PYTHON and so
# survives PyInstaller/cx_Freeze packaging without any extra configuration —
# native-binary backends like pypdfium2 need their DLL explicitly collected.
PDF_BACKENDS = ("pypdfium2", "fitz", "pdf2image", "pypdf")

_PDF_BACKEND = None
_PDF_BACKEND_NOTE = ""

# PDFium and PyMuPDF are not thread-safe. Every PDF render goes through this
# lock so the background preloader can never race the main thread.
_PDF_LOCK = threading.Lock()


def is_frozen():
    """True when running from a PyInstaller / cx_Freeze bundle."""
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def _resolve_pdf_backend():
    """Pick the first importable PDF backend.  Cached after the first call."""
    global _PDF_BACKEND, _PDF_BACKEND_NOTE
    if _PDF_BACKEND is not None:
        return _PDF_BACKEND

    tried = []
    for name in PDF_BACKENDS:
        try:
            mod = __import__(name)
            # pypdfium2 imports fine but blows up later if its native pdfium
            # binary wasn't bundled — prove it works before committing to it.
            if name == "pypdfium2":
                _ = mod.PdfDocument
            _PDF_BACKEND = name
            _PDF_BACKEND_NOTE = f"PDF preview via {name}"
            return _PDF_BACKEND
        except Exception as exc:
            tried.append(f"{name}: {type(exc).__name__}")
            continue

    _PDF_BACKEND = "none"
    _PDF_BACKEND_NOTE = (
        "No PDF preview backend available.\n"
        + ("This build is missing its PDF library.\n" if is_frozen() else "")
        + "Install one:  pip install pypdf   (pure Python, packaging-safe)"
    )
    return _PDF_BACKEND


def pdf_backend_label():
    _resolve_pdf_backend()
    return _PDF_BACKEND_NOTE


def _render_via_pypdf(path):
    """
    Pure-Python fallback: pull the largest embedded image out of page 1.

    This is not a true renderer — it can't rasterise vector or text content —
    but PDFs produced by this app (and most scanned documents) hold a single
    full-page image, so the preview is exact for those.
    """
    import pypdf
    reader = pypdf.PdfReader(path)
    n = len(reader.pages)
    if n == 0:
        return None, 0, "PDF has no pages"
    best = None
    try:
        for im in reader.pages[0].images:
            pil = im.image
            if best is None or (pil.width * pil.height) > (best.width * best.height):
                best = pil
    except Exception as exc:
        return None, n, f"Could not extract image: {exc}"
    if best is None:
        return None, n, ("No embedded image on page 1 — this PDF needs a full "
                         "renderer (pip install pypdfium2)")
    return best, n, ""


def render_pdf_page(path, scale=2.0):
    """
    Render page 1 of a PDF to a PIL image.
    Returns (image_or_None, page_count_or_None, note).

    All rendering is serialised through _PDF_LOCK. PDFium — the library behind
    pypdfium2 — is NOT thread-safe, and neither is PyMuPDF's default build.
    Calling them from the preload worker while the main thread renders the
    visible page produces intermittent SIGSEGV/SIGABRT crashes. Serialising is
    cheap here because decode time dominates, and it makes preloading safe.
    """
    backend = _resolve_pdf_backend()
    try:
        if backend == "pypdfium2":
            import pypdfium2 as pdfium
            with _PDF_LOCK:
                doc = pdfium.PdfDocument(path)
                n = len(doc)
                bitmap = doc[0].render(scale=scale)
                # .to_pil() returns an image that SHARES MEMORY with the
                # PDFium bitmap. Closing the document frees that buffer, so a
                # cached image would later be read from freed memory — an
                # intermittent segfault that only shows up once images outlive
                # the render call, i.e. exactly when preloading. .copy()
                # detaches the pixels into Python-owned memory.
                img = bitmap.to_pil().copy()
                del bitmap
                doc.close()
            return img, n, ""

        if backend == "fitz":
            import fitz
            with _PDF_LOCK:
                doc = fitz.open(path)
                n = doc.page_count
                pm = doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale))
                img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                doc.close()
            return img, n, ""

        if backend == "pdf2image":
            from pdf2image import convert_from_path
            pages = convert_from_path(path, dpi=int(72 * scale),
                                      first_page=1, last_page=1)
            return (pages[0] if pages else None), None, ""

        if backend == "pypdf":
            return _render_via_pypdf(path)

    except Exception as exc:
        return None, None, f"Could not render PDF: {exc}"

    return None, None, _PDF_BACKEND_NOTE


def load_visual(path, pdf_scale=2.0):
    """
    Open any supported file as a PIL image for display.
    Returns (image_or_None, info_dict).  info holds 'pages', 'note', 'error'.
    """
    info = {"pages": None, "note": "", "error": ""}
    tid = type_of(path)

    if tid == "pdf":
        img, pages, note = render_pdf_page(path, scale=pdf_scale)
        info["pages"], info["note"] = pages, note
        if img is None:
            info["error"] = note or "PDF could not be rendered"
        return img, info

    try:
        img = Image.open(path)
        # Multi-frame formats (animated GIF, multipage TIFF) — show frame 1
        n_frames = getattr(img, "n_frames", 1)
        if n_frames > 1:
            info["pages"] = n_frames
            img.seek(0)
        img.load()
        return img, info
    except Exception as exc:
        info["error"] = str(exc)
        return None, info


def load_config():
    """
    Read saved config.  Returns (bindings, settings).
    Handles both the new {"bindings":…, "settings":…} layout and the
    original flat {action: key} file, and upgrades legacy '<k>' bindings
    to the unambiguous '<Key-k>' form.
    """
    bindings = dict(DEFAULT_BINDINGS)
    settings = dict(DEFAULT_SETTINGS)
    path = CONFIG_PATH
    if not os.path.exists(path) and os.path.exists(LEGACY_CONFIG_PATH):
        path = LEGACY_CONFIG_PATH      # one-time migration from the old name
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return bindings, settings

    if not isinstance(data, dict):
        return bindings, settings

    raw_bindings = data.get("bindings") if "bindings" in data else data
    if isinstance(raw_bindings, dict):
        for aid, b in raw_bindings.items():
            if aid in DEFAULT_BINDINGS and isinstance(b, str):
                bindings[aid] = normalize_binding(b) if b else ""

    raw_settings = data.get("settings")
    if isinstance(raw_settings, dict):
        for k, v in raw_settings.items():
            if k in DEFAULT_SETTINGS and type(v) is type(DEFAULT_SETTINGS[k]):
                settings[k] = v

    return bindings, settings


def save_config(bindings, settings):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump({"bindings": bindings, "settings": settings}, f, indent=2)
        return True
    except OSError:
        return False


# ─── Image cache ──────────────────────────────────────────────────────────────
# Decoded images are large: a single 4096x4096 RGBA frame is 64 MB, so a
# 40-file folder of 4K textures would be ~2.7 GB if cached without limit.
# The cache is therefore bounded by BYTES, not by item count, and evicts
# least-recently-used entries once the budget is exceeded.
PRELOAD_BUDGET_MB = 1024


class ImageCache:
    """Thread-safe LRU cache of decoded (image, info) pairs, bounded by bytes."""

    def __init__(self, max_mb=PRELOAD_BUDGET_MB):
        self.max_bytes = int(max_mb) * 1024 * 1024
        self._d = OrderedDict()      # path -> (img, info, nbytes)
        self._bytes = 0
        self._lock = threading.Lock()

    @staticmethod
    def _size_of(img):
        if img is None:
            return 0
        try:
            return img.width * img.height * max(1, len(img.getbands()))
        except Exception:
            return 0

    def has(self, path):
        with self._lock:
            return path in self._d

    def get(self, path):
        with self._lock:
            hit = self._d.get(path)
            if hit is None:
                return None
            self._d.move_to_end(path)      # mark as recently used
            return hit[0], hit[1]

    def put(self, path, img, info):
        n = self._size_of(img)
        # A single image larger than the whole budget is never cached —
        # storing it would immediately evict everything else for no gain.
        if n > self.max_bytes:
            return False
        with self._lock:
            if path in self._d:
                self._bytes -= self._d[path][2]
                del self._d[path]
            self._d[path] = (img, info, n)
            self._bytes += n
            while self._bytes > self.max_bytes and len(self._d) > 1:
                _k, (_i, _f, nb) = self._d.popitem(last=False)
                self._bytes -= nb
        return True

    def drop(self, path):
        with self._lock:
            if path in self._d:
                self._bytes -= self._d[path][2]
                del self._d[path]

    def clear(self):
        with self._lock:
            self._d.clear()
            self._bytes = 0

    def stats(self):
        with self._lock:
            return len(self._d), self._bytes / 1024 / 1024, self.max_bytes / 1024 / 1024


# ─── Rounded button backgrounds ───────────────────────────────────────────────
# Tk's canvas has no anti-aliasing, so ovals and polygons come out with visibly
# stair-stepped edges. Drawing the shape in PIL at 4x and downsampling gives
# clean corners. Results are cached: a handful of distinct size/colour
# combinations covers the whole UI.
_RRECT_CACHE = {}
_RRECT_SS = 4          # supersampling factor


def _interp_key():
    """
    Identify the Tk interpreter that owns newly created images.

    A PhotoImage is registered inside one interpreter; handing it to another
    fails with 'image "pyimageN" doesn\'t exist'. Probing the cached object
    isn't reliable because the old interpreter may still be alive, so the
    cache is keyed by interpreter identity instead.
    """
    return id(getattr(tk, "_default_root", None))


def _hex_to_rgb(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rounded_rect_image(w, h, radius, fill, bg):
    """A PhotoImage of an anti-aliased rounded rectangle on `bg`."""
    if w <= 1 or h <= 1:
        return None
    key = (_interp_key(), w, h, radius, fill, bg)
    cached = _RRECT_CACHE.get(key)
    if cached is not None:
        try:
            cached.width()              # still owned by a live interpreter?
            return cached
        except Exception:
            _RRECT_CACHE.pop(key, None)

    try:
        ss = _RRECT_SS
        # Composite onto the parent colour rather than using alpha: Tk blends
        # transparent PhotoImages against black on some platforms, which would
        # leave dark halos around every corner.
        im = Image.new("RGB", (w * ss, h * ss), _hex_to_rgb(bg))
        ImageDraw.Draw(im).rounded_rectangle(
            [0, 0, w * ss - 1, h * ss - 1],
            radius=max(0, radius) * ss, fill=_hex_to_rgb(fill))
        photo = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS))
    except Exception:
        return None

    if len(_RRECT_CACHE) > 400:           # keep the cache bounded
        _RRECT_CACHE.clear()
    _RRECT_CACHE[key] = photo
    return photo


# ─── FlatButton ───────────────────────────────────────────────────────────────
class FlatButton(tk.Canvas):
    """
    A rounded-rectangle button drawn on a Canvas.

    Two reasons it isn't a tk.Button:

      1. macOS Aqua and the Windows theme silently ignore -background on a
         native button, so custom colours may or may not survive.
      2. Native buttons are square. Drawing the shape ourselves gives real
         rounded corners on every platform without a theme engine.

    Supports an optional left-aligned icon (a PhotoImage) beside the label,
    or an icon on its own for compact controls.
    """

    RADIUS  = 9
    PAD_X   = 15
    PAD_Y   = 9
    GAP     = 8      # space between icon and text
    FONT_BOOST = 1   # every button label one point larger

    def __init__(self, parent, text="", command=None, bg=BTN_NAV, hover=None,
                 fg="white", font_size=10, width=None, state=tk.NORMAL,
                 image=None, radius=None, **kw):
        super().__init__(parent, highlightthickness=0, bd=0, takefocus=0,
                         bg=self._parent_bg(parent), **kw)
        self._text     = text
        self._command  = command
        self._base_bg  = bg
        self._hover_bg = hover or bg
        self._fg       = fg
        self._state    = state
        self._image    = image
        self._radius   = self.RADIUS if radius is None else radius
        self._hovering = False
        self._font     = ("Helvetica", font_size + self.FONT_BOOST, "bold")
        self._min_chars = width

        self._lbl = _ButtonTextProxy(self)   # keeps .cget("text") working

        self._measure_and_draw()

        self.bind("<Button-1>",        self._on_click)
        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)
        self.bind("<Configure>",       self._on_configure)

    def _on_configure(self, event):
        # Only repaint when the allocated size really changed
        if (event.width, event.height) != getattr(self, "_last_size", None):
            self._last_size = (event.width, event.height)
            self._draw()

    @staticmethod
    def _parent_bg(parent):
        """Match the parent's colour so the rounded corners blend in."""
        try:
            return parent.cget("bg")
        except Exception:
            return BG_MID

    # ── Sizing ───────────────────────────────────────────────────────────────
    def _measure_and_draw(self):
        import tkinter.font as tkfont
        f = tkfont.Font(font=self._font)
        tw = f.measure(self._text) if self._text else 0
        th = f.metrics("linespace")

        iw = ih = 0
        if self._image is not None:
            try:
                iw, ih = self._image.width(), self._image.height()
            except Exception:
                self._image = None        # stale image from a closed window
        gap = self.GAP if (iw and self._text) else 0

        content_w = iw + gap + tw
        if self._min_chars:
            content_w = max(content_w, f.measure("0") * self._min_chars)

        w = content_w + self.PAD_X * 2
        h = max(th, ih) + self.PAD_Y * 2
        self.configure(width=w, height=h)
        self._draw()

    # ── Painting ─────────────────────────────────────────────────────────────
    def _draw(self):
        self.delete("all")
        # Use the size actually allocated by the geometry manager. A button
        # packed with fill=X is stretched well beyond its requested width, and
        # reading the configured width instead would draw the shape far too
        # narrow — leaving a stubby pill floating in a wider clickable area.
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:                 # not mapped yet
            w, h = int(self["width"]), int(self["height"])

        col = (self._hover_bg if (self._hovering and self._state == tk.NORMAL)
               else self._base_bg)
        self._bg_photo = rounded_rect_image(w, h, self._radius, col,
                                            self._parent_bg(self.master))
        if self._bg_photo is not None:
            self.create_image(0, 0, anchor="nw", image=self._bg_photo)

        fg = "#7a7a96" if self._state == tk.DISABLED else self._fg
        iw = 0
        if self._image is not None:
            try:
                iw = self._image.width()
            except Exception:
                self._image = None
        tw = 0
        if self._text:
            import tkinter.font as tkfont
            tw = tkfont.Font(font=self._font).measure(self._text)
        gap = self.GAP if (iw and self._text) else 0
        total = iw + gap + tw
        x = (w - total) / 2

        if self._image is not None:
            self.create_image(x, h / 2, anchor="w", image=self._image)
            x += iw + gap
        if self._text:
            self.create_text(x, h / 2, anchor="w", text=self._text,
                             fill=fg, font=self._font)

    # ── Interaction ──────────────────────────────────────────────────────────
    def _on_click(self, _e):
        if self._state == tk.NORMAL and self._command:
            self._command()
        return "break"

    def _on_enter(self, _e):
        self._hovering = True
        if self._state == tk.NORMAL:
            self.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _e):
        self._hovering = False
        self._draw()

    # ── Config passthrough ───────────────────────────────────────────────────
    def configure(self, **kw):
        redraw = resize = False
        if "text" in kw:
            self._text = kw.pop("text"); resize = True
        if "image" in kw:
            self._image = kw.pop("image"); resize = True
        if "hover" in kw:
            self._hover_bg = kw.pop("hover"); redraw = True
        if "bg" in kw:
            self._base_bg = kw.pop("bg"); redraw = True
        if "fg" in kw:
            self._fg = kw.pop("fg"); redraw = True
        if "state" in kw:
            self._state = kw.pop("state"); redraw = True
        if kw:
            super().configure(**kw)
        if resize:
            self._measure_and_draw()
        elif redraw:
            self._draw()

    config = configure


class _ButtonTextProxy:
    """Small shim so button.cget-style label access keeps working."""

    def __init__(self, btn):
        self._btn = btn

    def cget(self, key):
        if key == "text":
            return self._btn._text
        if key in ("fg", "foreground"):
            return self._btn._fg
        raise KeyError(key)

    def __getattr__(self, attr):
        # The label is no longer a separate widget; forward anything else
        # (event_generate, winfo_*, bind ...) to the button canvas.
        return getattr(self.__dict__["_btn"], attr)


# ─── FlatScrollbar ────────────────────────────────────────────────────────────
class FlatScrollbar(tk.Canvas):
    """
    A scrollbar drawn on a Canvas so the thumb colour is guaranteed.

    Same reasoning as FlatButton: tk.Scrollbar defers to the platform theme
    on Windows and macOS and quietly ignores -background / -troughcolor, so a
    custom thumb colour may or may not survive. Drawing it ourselves removes
    the guesswork and keeps the widget legible on the dark UI everywhere.

    Drop-in compatible with the parts of the Tk scrollbar protocol that
    matter: pass `command=widget.yview` and set `widget['yscrollcommand']`
    to this widget's `set`.
    """

    def __init__(self, parent, command=None, width=13, orient="vertical",
                 trough=BG_DARK, thumb=THUMB, thumb_hover=THUMB_HOVER,
                 thumb_drag=THUMB_DRAG, min_thumb=28, **kw):
        self._horizontal = orient.startswith("h")
        size_kw = {"height": width} if self._horizontal else {"width": width}
        super().__init__(parent, bg=trough, highlightthickness=0, bd=0,
                         takefocus=0, **size_kw, **kw)
        self.command = command
        self._first, self._last = 0.0, 1.0
        self._trough = trough
        self._c_idle, self._c_hover, self._c_drag = thumb, thumb_hover, thumb_drag
        self._min_thumb = min_thumb
        self._hover = False
        self._drag_dy = None          # grab offset inside the thumb

        self.bind("<Configure>",        lambda e: self._redraw())
        self.bind("<Button-1>",         self._on_press)
        self.bind("<B1-Motion>",        self._on_drag)
        self.bind("<ButtonRelease-1>",  self._on_release)
        self.bind("<Enter>",            self._on_enter)
        self.bind("<Leave>",            self._on_leave)
        self.bind("<MouseWheel>",       self._on_wheel)         # Windows/macOS
        self.bind("<Button-4>",         lambda e: self._scroll(-1))
        self.bind("<Button-5>",         lambda e: self._scroll(1))

    # ── Scrollbar protocol ───────────────────────────────────────────────────
    def configure(self, **kw):
        # `command` is not a Canvas option, so intercept it here. This keeps
        # the familiar sb.config(command=widget.yview) call working.
        if "command" in kw:
            self.command = kw.pop("command")
        if kw:
            super().configure(**kw)

    config = configure

    def set(self, first, last):
        self._first, self._last = float(first), float(last)
        self._redraw()

    def get(self):
        return self._first, self._last

    # ── Geometry ─────────────────────────────────────────────────────────────
    def _extent(self):
        return self.winfo_width() if self._horizontal else self.winfo_height()

    def _thumb_bounds(self):
        """Pixel span of the thumb, or None when nothing is scrollable."""
        h = self._extent()
        if h <= 1:
            return None
        frac = self._last - self._first
        if frac >= 0.999:
            return None                       # everything fits: hide the thumb
        th = max(self._min_thumb, int(h * frac))
        th = min(th, h)
        # The thumb is padded to a minimum height, so it travels across a
        # shorter track than the raw fraction implies — scale accordingly or
        # it overshoots the bottom.
        travel = h - th
        y0 = int(self._first / max(1e-9, (1.0 - frac)) * travel) if frac < 1 else 0
        y0 = max(0, min(travel, y0))
        return y0, y0 + th

    def _redraw(self):
        self.delete("all")
        self.configure(bg=self._trough)
        b = self._thumb_bounds()
        if b is None:
            return
        y0, y1 = b
        thick = self.winfo_height() if self._horizontal else self.winfo_width()
        pad = 3
        r = (thick - pad * 2) / 2
        col = (self._c_drag if self._drag_dy is not None
               else self._c_hover if self._hover else self._c_idle)
        if self._horizontal:
            self.create_oval(y0, pad, y0 + 2 * r, thick - pad, fill=col, width=0)
            self.create_oval(y1 - 2 * r, pad, y1, thick - pad, fill=col, width=0)
            self.create_rectangle(y0 + r, pad, y1 - r, thick - pad, fill=col, width=0)
        else:
            self.create_oval(pad, y0, thick - pad, y0 + 2 * r, fill=col, width=0)
            self.create_oval(pad, y1 - 2 * r, thick - pad, y1, fill=col, width=0)
            self.create_rectangle(pad, y0 + r, thick - pad, y1 - r, fill=col, width=0)

    # ── Interaction ──────────────────────────────────────────────────────────
    def _on_press(self, event):
        b = self._thumb_bounds()
        if b is None:
            return
        y0, y1 = b
        pos = event.x if self._horizontal else event.y
        event = type("E", (), {"x": event.x, "y": event.y, "_p": pos})()
        if y0 <= pos <= y1:
            self._drag_dy = event._p - y0      # grabbed the thumb
        else:
            # Clicked the trough: jump so the thumb centres on the click
            self._drag_dy = (y1 - y0) // 2
            self._move_to(event._p)
        self._redraw()

    def _on_drag(self, event):
        if self._drag_dy is not None:
            self._move_to(event.x if self._horizontal else event.y)

    def _on_release(self, _event):
        self._drag_dy = None
        self._redraw()

    def _move_to(self, y):
        h = self._extent()
        b = self._thumb_bounds()
        if b is None or not self.command:
            return
        th = b[1] - b[0]
        travel = max(1, h - th)
        top = max(0, min(travel, y - (self._drag_dy or 0)))
        frac = self._last - self._first
        self.command("moveto", (top / travel) * (1.0 - frac))

    def _on_wheel(self, event):
        self._scroll(-1 if event.delta > 0 else 1)

    def _scroll(self, direction):
        if self.command:
            self.command("scroll", direction, "units")

    def _on_enter(self, _e):
        self._hover = True
        self._redraw()

    def _on_leave(self, _e):
        self._hover = False
        self._redraw()


# ─── ScrollFrame ──────────────────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    """
    A vertically scrollable container.

    Dialogs that grow with content (the shortcut list is 26 rows and counting)
    otherwise push their own footer off the bottom of the screen, hiding Save.
    Putting the variable-height part in here keeps the action buttons pinned
    and reachable no matter how long the list gets.

    Use `.body` as the parent for child widgets.
    """

    def __init__(self, parent, bg=BG_DARK, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = FlatScrollbar(self, command=self.canvas.yview, trough=bg)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        for w in (self.canvas, self.body):
            w.bind("<MouseWheel>", self._on_wheel)
            w.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
            w.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _on_body_configure(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Match the inner frame to the canvas width so content doesn't clip
        self.canvas.itemconfigure(self._win, width=event.width)

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def bind_wheel_recursive(self, widget=None):
        """Let the wheel scroll even when the cursor is over a child widget."""
        widget = widget or self.body
        widget.bind("<MouseWheel>", self._on_wheel)
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children():
            self.bind_wheel_recursive(child)

    def wanted_height(self):
        self.body.update_idletasks()
        return self.body.winfo_reqheight()

    def fit_content(self, max_height=None, max_width=None):
        """
        Size the scroll canvas to its contents.

        A Canvas reports no requested size from a create_window child, so a
        dialog built around one sizes itself as if the body were empty — which
        is why the shortcut columns were clipped on the right. Pushing the
        body's requested size onto the canvas lets the dialog measure itself
        correctly.
        """
        self.body.update_idletasks()
        w = self.body.winfo_reqwidth()
        h = self.body.winfo_reqheight()
        if max_width:
            w = min(w, max_width)
        if max_height:
            h = min(h, max_height)
        self.canvas.configure(width=w, height=h)


def fit_to_screen(win, margin=110):
    """
    Clamp a dialog to the visible screen and centre it.

    Without this a tall dialog can open with its lower half — including the
    Save button — below the bottom of the display, with no way to reach it.
    """
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    h = min(h, sh - margin)
    w = min(w, sw - 40)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 3)
    win.geometry(f"{w}x{h}+{x}+{y}")


# ─── FlowBar ──────────────────────────────────────────────────────────────────
class FlowBar(tk.Frame):
    """
    A horizontal bar whose children wrap onto extra rows when space runs out.

    Tk's packer has no concept of overflow: children packed to the left and
    right of the same frame simply draw on top of each other once the window
    is too narrow, which is how "Reset" ended up half-hidden behind the zoom
    controls. This measures every child and lays them out with place(),
    stacking additional rows and growing its own height instead of colliding.
    """

    HGAP = 6
    VGAP = 5

    def __init__(self, parent, bg=BG_MID, hgap=None, vgap=None, pady=0, **kw):
        super().__init__(parent, bg=bg, **kw)
        self._items = []              # [(widget, side)]
        self._hgap = self.HGAP if hgap is None else hgap
        self._vgap = self.VGAP if vgap is None else vgap
        self._pady = pady
        self._last_w = -1
        self._child_sizes = {}
        self._reflow_job = None
        self.bind("<Configure>", self._on_configure)

    def add(self, widget, side="left"):
        """side is a hint used only while everything fits on one row."""
        self._items.append((widget, side))
        # A child that changes label (compact mode, shortcut hints, live
        # counts) changes width without the bar itself being reconfigured.
        # Watching each child keeps the layout honest; only real size changes
        # trigger a reflow, so place() repositioning can't loop.
        widget.bind("<Configure>", self._on_child_configure, add="+")
        return widget

    def _on_child_configure(self, event):
        key = id(event.widget)
        size = (event.width, event.height)
        if self._child_sizes.get(key) == size:
            return
        self._child_sizes[key] = size
        self._schedule_reflow()

    def _schedule_reflow(self):
        if self._reflow_job is None:
            self._reflow_job = self.after_idle(self._do_scheduled_reflow)

    def _do_scheduled_reflow(self):
        self._reflow_job = None
        self.reflow()

    def _on_configure(self, event):
        if event.width != self._last_w:
            self._last_w = event.width
            self._schedule_reflow()

    def reflow(self):
        if not self._items:
            return
        avail = self.winfo_width()
        if avail <= 1:
            self.after(30, self.reflow)
            return

        widths, heights = [], []
        for w, _s in self._items:
            w.update_idletasks()
            widths.append(w.winfo_reqwidth())
            heights.append(w.winfo_reqheight())

        need = sum(widths) + self._hgap * (len(widths) - 1)
        row_h = max(heights) if heights else 0

        if need <= avail:
            # Everything fits: honour the left/right placement hint
            x = 0
            for i, (w, side) in enumerate(self._items):
                if side == "left":
                    w.place(x=x, y=self._pady + (row_h - heights[i]) // 2)
                    x += widths[i] + self._hgap
            x = avail
            for i in range(len(self._items) - 1, -1, -1):
                w, side = self._items[i]
                if side == "right":
                    x -= widths[i]
                    w.place(x=x, y=self._pady + (row_h - heights[i]) // 2)
                    x -= self._hgap
            self.configure(height=row_h + self._pady * 2)
            return

        # Too narrow: wrap into left-aligned rows, preserving order
        y = self._pady
        x = 0
        rows = 1
        for i, (w, _side) in enumerate(self._items):
            if x and x + widths[i] > avail:
                x = 0
                y += row_h + self._vgap
                rows += 1
            w.place(x=x, y=y + (row_h - heights[i]) // 2)
            x += widths[i] + self._hgap
        self.configure(height=rows * row_h + (rows - 1) * self._vgap
                              + self._pady * 2)


# ─── Main Application ─────────────────────────────────────────────────────────
class VisManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1280x800")
        self.root.minsize(960, 620)
        self.root.configure(bg=BG_DARK)

        # ── State ──
        self.base_dir        = None
        self.folder_list     = []           # ordered list of folder paths
        self.folders         = {}           # {folder_path: [tga_file, …]}
        self.image_states    = {}           # {filepath: True=keep / False=delete}
        # Flags and notes are independent of Keep/Delete: a file can be
        # flagged for follow-up whether it is being kept or discarded.
        self.notes           = {}           # {filepath: note text ("" = flag only)}
        self.transforms      = {}           # {filepath: (rot 0-3, mirror bool)}
        self.notes_exported  = True         # False once notes change unexported
        self._scene          = None         # active CubeScene, if any
        self._scene_path     = None
        self._scene_error    = ""
        self.cur_folder_idx  = 0
        self.cur_image_idx   = 0
        self._photo          = None         # ImageTk ref (prevents GC)
        self._resize_job     = None         # debounce id
        self._quality_job    = None         # deferred high-quality redraw
        self._pan_job        = None         # coalesced pan redraw
        self._resize_paint_job = None       # live repaint while resizing
        self._mip            = None         # downscaled copy for fast zoom-out
        self._mip_src        = None
        self._mip_factor     = 1

        # ── Zoom / pan state ──
        self._src_img   = None    # full-resolution PIL image of current file
        self._fit_scale = 1.0     # scale at which the image exactly fits
        self._zoom      = 1.0     # multiplier on top of fit (1.0 == fit)
        self._ox        = 0.0     # canvas x of source pixel (0,0)
        self._oy        = 0.0
        self._pan_from  = None    # drag anchor while panning
        self._panned    = False

        # ── Cache / preload ──
        self._cache          = ImageCache()
        self._preload_thread = None
        self._preload_stop   = None
        self._preload_q      = None
        self._preload_job    = None
        self._preload_total  = 0
        self._preload_done   = 0

        # ── Key bindings & settings ──
        self.bindings, self.settings = load_config()
        self._bound_seqs = []               # sequences currently bound to root
        self._shortcut_btns = {}            # {action_id: FlatButton}

        self._build_ui()
        self._bind_keys()
        self._compact = None
        self._apply_responsive(self.root.winfo_width() or 1280)
        self._refresh_shortcut_labels()
        self._refresh_preload_btn()
        self.root.bind("<Configure>", self._on_root_configure)

    # ─────────────────────────────────────────────────────── UI construction ──

    def _build_ui(self):
        self._build_toolbar()

        # Paned window: sidebar | viewer
        self._pane = pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                              sashwidth=5, sashrelief=tk.FLAT,
                              bg=BORDER, handlepad=0, handlesize=0)
        pane.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 0))

        self._build_sidebar(pane)
        self._build_viewer(pane)

        self._build_statusbar()

    # ── Toolbar ──────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        self._toolbar = outer = tk.Frame(self.root, bg=BG_MID, pady=6, padx=12)
        outer.pack(side=tk.TOP, fill=tk.X)
        tb = FlowBar(outer, bg=BG_MID, hgap=8)
        tb.pack(fill=tk.X)
        self._tb_flow = tb

        # ── Brand: logo mark + wordmark, with a text fallback ──
        brand = tk.Frame(tb, bg=BG_MID)
        tb.add(brand, "left")

        # Pre-rendered 32px asset — Tk's subsample() is nearest-neighbour and
        # turns fine logo detail to mush, so the resize is done ahead of time.
        self._logo_img = _photo_from_b64(LOGO_SMALL_PNG_B64)
        if self._logo_img is not None:
            tk.Label(brand, image=self._logo_img, bg=BG_MID).pack(
                side=tk.LEFT, padx=(0, 9))

        self._wordmark_img = _photo_from_b64(WORDMARK_PNG_B64)
        if self._wordmark_img is not None:
            tk.Label(brand, image=self._wordmark_img, bg=BG_MID).pack(side=tk.LEFT)
        else:
            tk.Label(brand, text=APP_NAME, bg=BG_MID, fg=ACCENT_BLUE,
                     font=("Helvetica", 15, "bold")).pack(side=tk.LEFT)

        # Open
        self.open_btn = self._btn(tb, "Open Directory", self.browse_directory,
                                  image=icon("folder"),
                                  bg=BTN_OPEN, hover=BTN_OPEN_HOV)
        tb.add(self.open_btn, "left")
        self._shortcut_btns["open_dir"] = (self.open_btn, "Open Directory")

        # Open folder name — this is the primary "where am I" cue, so it gets
        # real weight instead of the muted 10pt it had before.
        self.dir_lbl = tk.Label(tb, text="No directory selected", bg=BG_MID,
                                fg=TEXT_MUTED, font=("Helvetica", 13, "bold"))
        tb.add(self.dir_lbl, "left")

        # Right: process, shortcuts, stats
        self.process_btn = self._btn(tb, f"{GLYPHS['process']}  Process Images", self.process_images,
                                     bg=BTN_PROCESS, hover=BTN_PROCESS_HOV,
                                     state=tk.DISABLED)
        tb.add(self.process_btn, "right")
        self._shortcut_btns["process"] = (self.process_btn, f"{GLYPHS['process']}  Process Images")

        self.export_btn = self._btn(
            tb, "Export Notes", self.export_notes, image=icon("edit-document"),
            bg="#7c3aed", hover="#8b5cf6")
        tb.add(self.export_btn, "right")
        self._shortcut_btns["export_notes"] = (self.export_btn,
                                               "Export Notes")

        self.help_btn = self._btn(tb, "?", self.open_help,
                                  bg=BTN_INVERT, hover="#606878", font_size=11)
        tb.add(self.help_btn, "right")

        self.keys_btn = self._btn(tb, "Shortcuts", self.open_shortcuts_dialog,
                                  image=icon("keyboard"),
                                  bg=BTN_KEYS, hover=BTN_KEYS_HOV)
        tb.add(self.keys_btn, "right")

        # Counts split into separate labels so each can carry its own colour;
        # a single label can only be one colour, which is why the old readout
        # was a uniform grey blur.
        stats = tk.Frame(tb, bg=BG_MID)
        tb.add(stats, "right")
        self._stats_frame = stats

        self.keep_stat = tk.Label(stats, text="", bg=BG_MID, fg=BTN_KEEP_HOV,
                                  font=("Helvetica", 13, "bold"))
        self.keep_stat.pack(side=tk.LEFT)
        self.del_stat = tk.Label(stats, text="", bg=BG_MID, fg=BTN_DEL_HOV,
                                 font=("Helvetica", 13, "bold"))
        self.del_stat.pack(side=tk.LEFT, padx=(12, 0))
        self.flag_stat = tk.Label(stats, text="", bg=BG_MID, fg=FLAG_TEXT,
                                  font=("Helvetica", 13, "bold"))
        self.flag_stat.pack(side=tk.LEFT, padx=(12, 0))
        self.total_stat = tk.Label(stats, text="", bg=BG_MID, fg=TEXT_MUTED,
                                   font=("Helvetica", 11))
        self.total_stat.pack(side=tk.LEFT, padx=(12, 0))

        # Kept for compatibility with code that used one combined label
        self.stats_lbl = self.total_stat

    # ── Sidebar ──────────────────────────────────────────────────────────────
    def _build_sidebar(self, pane):
        self._sidebar = sidebar = tk.Frame(pane, bg=BG_SIDEBAR, width=210)
        pane.add(sidebar, minsize=170, stretch="never")

        # Loading mode belongs with the folder list it governs, not on the
        # strip above the image.
        fhdr = tk.Frame(sidebar, bg=BG_SIDEBAR)
        fhdr.pack(fill=tk.X, padx=8, pady=(10, 4))
        tk.Label(fhdr, text="FOLDERS", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)

        self.preload_btn = self._btn(fhdr, "", self.toggle_preload,
                                     bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=8)
        self.preload_btn.pack(side=tk.RIGHT)
        self._shortcut_btns["preload"] = (self.preload_btn, "")

        self.cache_lbl = tk.Label(sidebar, text="", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                                  font=("Helvetica", 8))
        self.cache_lbl.pack(anchor=tk.W, padx=10)

        # Listbox, with its own frame so a horizontal bar can sit beneath it
        lf_outer = tk.Frame(sidebar, bg=BG_SIDEBAR)
        lf_outer.pack(fill=tk.BOTH, expand=True, padx=6)
        lf = tk.Frame(lf_outer, bg=BG_SIDEBAR)
        lf.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sb = FlatScrollbar(lf, trough=BG_DARK)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_sb = sb

        self.folder_lb = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg=BG_DARK, fg=TEXT_PRIMARY,
            selectbackground=ACCENT_BLUE, selectforeground="white",
            activestyle="none", borderwidth=0, highlightthickness=0,
            font=("Helvetica", 10), relief=tk.FLAT,
        )
        self.folder_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.folder_lb.yview)

        # Deeply-nested folder names run well past the sidebar width, and a
        # truncated name like "1a_dicationSinglet_HOM..." is unusable when
        # several differ only in their suffix. A horizontal bar lets the name
        # be read in full without widening the whole panel.
        hsb = FlatScrollbar(lf_outer, orient="horizontal", width=11,
                            trough=BG_SIDEBAR)
        hsb.pack(side=tk.BOTTOM, fill=tk.X, pady=(2, 0))
        hsb.config(command=self.folder_lb.xview)
        self.folder_lb.config(xscrollcommand=hsb.set)
        self.folder_hsb = hsb

        # Shift+wheel scrolls sideways, matching every other list widget
        self.folder_lb.bind(
            "<Shift-MouseWheel>",
            lambda e: self.folder_lb.xview_scroll(-1 if e.delta > 0 else 1, "units"))

        # Wheel over the list itself, not just over the scrollbar
        self.folder_lb.bind(
            "<MouseWheel>",
            lambda e: self.folder_lb.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.folder_lb.bind("<Button-4>",
                            lambda e: self.folder_lb.yview_scroll(-1, "units"))
        self.folder_lb.bind("<Button-5>",
                            lambda e: self.folder_lb.yview_scroll(1, "units"))
        self.folder_lb.bind("<<ListboxSelect>>", self._on_folder_select)

        # ── File type filter ──
        sep0 = tk.Frame(sidebar, bg=BORDER, height=1)
        sep0.pack(fill=tk.X, padx=6, pady=(8, 0))

        tk.Label(sidebar, text="FILE TYPES", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(pady=(8, 2), padx=10, anchor=tk.W)

        self.type_filter_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        self.type_filter_frame.pack(fill=tk.X, padx=6)
        self._type_rows = {}

        # Quick actions
        sep = tk.Frame(sidebar, bg=BORDER, height=1)
        sep.pack(fill=tk.X, padx=6, pady=6)

        qa = tk.Frame(sidebar, bg=BG_SIDEBAR)
        qa.pack(fill=tk.X, padx=6, pady=(0, 8))
        b_keep_all = self._btn(qa, f"{GLYPHS['keep']} Keep All in Folder", self.keep_all_folder,
                               bg=BTN_KEEP_SB, hover=BTN_KEEP, font_size=9)
        b_keep_all.pack(fill=tk.X, pady=2)
        self._shortcut_btns["keep_all"] = (b_keep_all, f"{GLYPHS['keep']} Keep All")

        b_del_all = self._btn(qa, f"{GLYPHS['delete']} Delete All in Folder", self.delete_all_folder,
                              bg=BTN_DEL_SB, hover=BTN_DEL, font_size=9)
        b_del_all.pack(fill=tk.X, pady=2)
        self._shortcut_btns["delete_all"] = (b_del_all, f"{GLYPHS['delete']} Delete All")

        b_invert = self._btn(qa, f"{GLYPHS['invert']} Invert Folder", self.invert_folder,
                             bg=BTN_INVERT, hover="#606878", font_size=9)
        b_invert.pack(fill=tk.X, pady=2)
        self._shortcut_btns["invert"] = (b_invert, f"{GLYPHS['invert']} Invert")

    # ── Viewer ───────────────────────────────────────────────────────────────
    def _build_viewer(self, pane):
        viewer = tk.Frame(pane, bg=BG_DARK)
        pane.add(viewer, minsize=620, stretch="always")
        self._viewer = viewer

        # ── Large position header ──
        self._header = header = tk.Frame(viewer, bg=BG_DARK, pady=8)
        header.pack(side=tk.TOP, fill=tk.X)

        self.big_pos_lbl = tk.Label(
            header, text="\u2014", bg=BG_DARK, fg=TEXT_PRIMARY,
            font=("Helvetica", 30, "bold"),
        )
        self.big_pos_lbl.pack()

        self.big_ctx_lbl = tk.Label(
            header, text="No directory loaded", bg=BG_DARK, fg=TEXT_MUTED,
            font=("Helvetica", 10),
        )
        self.big_ctx_lbl.pack()

        # Preload progress — hidden unless a folder load is in flight
        self.load_frame = tk.Frame(header, bg=BG_DARK)
        self.load_lbl = tk.Label(self.load_frame, text="", bg=BG_DARK,
                                 fg="#fbbf24", font=("Helvetica", 9, "bold"))
        self.load_lbl.pack()
        self.load_bar = ttk.Progressbar(self.load_frame, maximum=100, length=300)
        self.load_bar.pack(pady=(2, 0))

        # Thin progress bar showing position within the current folder
        self.prog_canvas = tk.Canvas(header, height=4, bg=BORDER,
                                     highlightthickness=0)
        self.prog_canvas.pack(fill=tk.X, padx=40, pady=(8, 0))
        self.prog_canvas.bind("<Configure>", lambda e: self._draw_progress())

        # ── Status strip: things that are not image manipulation ──
        self._zbar = zouter = tk.Frame(viewer, bg=BG_DARK)
        zouter.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(2, 4))
        zbar = FlowBar(zouter, bg=BG_DARK, hgap=6)
        zbar.pack(fill=tk.X)
        self._zb_flow = zbar

        self.zoom_hint = tk.Label(
            zbar, text="scroll to zoom  \u2022  drag to pan  \u2022  "
                       "double-click toggles fit / 1:1",
            bg=BG_DARK, fg=TEXT_MUTED, font=("Helvetica", 8))
        zbar.add(self.zoom_hint, "left")

        # The bottom action bar must be packed BEFORE the toolbar and canvas.
        # Pack fills in order, so a canvas with expand=True claims everything
        # left over — packing the bar afterwards squeezed it into a strip down
        # the right-hand side instead of across the bottom.
        self._build_action_bar(viewer)

        # ── Left vertical toolbar: everything that alters the view ──
        # Grouping rotate/flip/zoom into one column keeps them together and
        # off the horizontal bars, which is what kept running out of width.
        self._build_view_toolbar(viewer)

        # Canvas
        self.canvas = tk.Canvas(viewer, bg=BG_DARK, highlightthickness=0,
                                cursor="crosshair")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Wheel zoom. Windows/macOS send <MouseWheel>; X11 sends Button-4/5.
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel(e, force=120))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel(e, force=-120))
        # Drag to pan
        self.canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<B1-Motion>", self._on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    # ── Left view toolbar ────────────────────────────────────────────────────
    def _build_view_toolbar(self, viewer):
        """
        Vertical strip holding every control that alters the view.

        Laid out in paired rows rather than a single column: stacking Fit and
        1:1 made the strip taller than short windows, so the bottom controls
        were cut off with no way to reach them.
        """
        # The strip lives inside a scroller. Shedding captions buys ~70px,
        # which is enough for a slightly short window but not for a genuinely
        # small one — without scrolling the zoom controls simply fall off the
        # bottom with no way to reach them.
        outer = tk.Frame(viewer, bg=BG_SIDEBAR)
        outer.pack(side=tk.LEFT, fill=tk.Y)
        self._view_tb = outer

        scroller = ScrollFrame(outer, bg=BG_SIDEBAR)
        scroller.pack(fill=tk.BOTH, expand=True)
        self._vtb_scroll = scroller

        tb = tk.Frame(scroller.body, bg=BG_SIDEBAR, padx=9, pady=9)
        tb.pack(fill=tk.BOTH, expand=True)
        self._vtb_body = tb

        # Section headings and dividers are the first things dropped when the
        # window is too short to show the whole strip — losing a caption is a
        # far better outcome than losing the zoom buttons off the bottom.
        self._vtb_optional = []

        def head(text):
            lbl = tk.Label(tb, text=text, bg=BG_SIDEBAR, fg=TEXT_MUTED,
                           font=("Helvetica", 7, "bold"))
            lbl.pack(pady=(9, 4))
            self._vtb_optional.append((lbl, {"pady": (9, 4)}))

        def pair(items):
            row = tk.Frame(tb, bg=BG_SIDEBAR)
            row.pack(pady=3)
            out = []
            for kind, val, cmd in items:
                if kind == "icon":
                    b = self._btn(row, "", cmd, image=icon(val),
                                  bg=BTN_NAV, hover=BTN_NAV_HOV)
                else:
                    b = self._btn(row, val, cmd, bg=BTN_NAV,
                                  hover=BTN_NAV_HOV, font_size=8, width=3)
                b.pack(side=tk.LEFT, padx=5)
                out.append(b)
            return out

        head("ROTATE")
        pair([("icon", "undo", self.rotate_ccw),
              ("icon", "redo", self.rotate_cw)])

        head("FLIP")
        pair([("icon", "flip-horizontal", self.flip_horizontal),
              ("icon", "flip-vertical", self.flip_vertical)])

        self.rot_lbl = tk.Label(tb, text="\u2014", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                                font=("Helvetica", 8, "bold"))
        self.rot_lbl.pack(pady=(7, 3))
        self._btn(tb, "Reset", self.reset_transform, bg=BTN_INVERT,
                  hover="#606878", font_size=8).pack(fill=tk.X, pady=(0, 5))

        sep1 = tk.Frame(tb, bg=BORDER, height=1)
        sep1.pack(fill=tk.X, pady=8)
        self._vtb_optional.append((sep1, {"fill": tk.X, "pady": 8}))

        head("ZOOM")
        pair([("icon", "collapse", self.zoom_out),
              ("icon", "expand", self.zoom_in)])

        self.zoom_lbl = tk.Label(tb, text="Fit", bg=BG_SIDEBAR, fg=TEXT_PRIMARY,
                                 font=("Helvetica", 9, "bold"))
        self.zoom_lbl.pack(pady=(7, 4))

        self.zoom_fit_btn, self.zoom_100_btn = pair(
            [("text", "Fit", self.zoom_fit), ("text", "1:1", self.zoom_actual)])

        sep2 = tk.Frame(tb, bg=BORDER, height=1)
        sep2.pack(fill=tk.X, pady=8)
        self._vtb_optional.append((sep2, {"fill": tk.X, "pady": 8}))
        self.fs_btn = self._btn(tb, "", self.toggle_fullscreen,
                                image=icon("corners"),
                                bg=BTN_KEYS, hover=BTN_KEYS_HOV)
        self.fs_btn.pack(pady=(5, 3))
        self._shortcut_btns["fullscreen"] = (self.fs_btn, "")

        # 3D section — packed and unpacked as cube files come and go
        self._cube_sec = tk.Frame(tb, bg=BG_SIDEBAR)
        tk.Frame(self._cube_sec, bg=BORDER, height=1).pack(fill=tk.X, pady=6)
        tk.Label(self._cube_sec, text="3D", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Helvetica", 7, "bold")).pack(pady=(2, 4))
        self._btn(self._cube_sec, "Iso", self.open_cube_settings,
                  bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=8).pack(fill=tk.X, pady=2)
        self._btn(self._cube_sec, "Export", self.open_cube_export,
                  bg="#6d28d9", hover="#7c3aed", font_size=8).pack(fill=tk.X, pady=2)
        self._btn(self._cube_sec, "Recenter", self.cube_reset,
                  bg=BTN_INVERT, hover="#606878", font_size=8).pack(fill=tk.X, pady=2)

        self._vtb_compact = False
        scroller.bind_wheel_recursive()
        self.root.after(80, self._fit_view_toolbar)
        outer.bind("<Configure>", self._on_view_tb_configure)

    def _fit_view_toolbar(self):
        """Match the scroll canvas to the strip so its width is respected."""
        try:
            body = self._vtb_body
            body.update_idletasks()
            self._vtb_scroll.canvas.configure(width=body.winfo_reqwidth())
        except Exception:
            pass

    def _on_view_tb_configure(self, event):
        """Drop captions when the strip no longer fits, restore them when it does."""
        body = getattr(self, "_vtb_body", None)
        if body is None:
            return
        need = body.winfo_reqheight()
        if self._vtb_compact:
            extra = sum(w.winfo_reqheight() + 8 for w, _k in self._vtb_optional)
            if event.height > need + extra + 6:
                self._set_vtb_compact(False)
        elif need > event.height:
            self._set_vtb_compact(True)

    def _set_vtb_compact(self, compact):
        """
        Hide or restore the optional widgets, preserving their position.

        pack() appends to the end of the parent, so naively re-packing after
        pack_forget() would shuffle the strip into a different order. Each
        widget's following sibling is recorded on the way out and used as a
        `before` anchor on the way back, restoring in reverse so the anchor
        always exists by the time it is needed.
        """
        if compact == self._vtb_compact:
            return
        self._vtb_compact = compact

        if compact:
            kids = self._vtb_body.winfo_children()
            for w, kw in self._vtb_optional:
                try:
                    i = kids.index(w)
                    kw["_before"] = kids[i + 1] if i + 1 < len(kids) else None
                except ValueError:
                    kw["_before"] = None
            for w, _kw in self._vtb_optional:
                w.pack_forget()
        else:
            for w, kw in reversed(self._vtb_optional):
                before = kw.pop("_before", None)
                opts = {k: v for k, v in kw.items() if not k.startswith("_")}
                try:
                    if before is not None and before.winfo_exists():
                        w.pack(before=before, **opts)
                    else:
                        w.pack(**opts)
                except tk.TclError:
                    w.pack(**opts)

    # ── Bottom action bar ────────────────────────────────────────────────────
    def _build_action_bar(self, viewer):
        """
        The marking controls, laid out in a grid that reflows with width.

        Wide  →  one row:   [<<] [<] KEEP DELETE Note Flag [>] [>>]
        Narrow →  two rows: [<<] KEEP DELETE [>>]
                            [ <] Note Flag   [ >]

        The single row is worth having: it is one button-height shorter, and
        that height goes straight to the image.
        """
        self._nav = nav = tk.Frame(viewer, bg=BG_MID, pady=6)
        nav.pack(side=tk.BOTTOM, fill=tk.X)

        self.img_name_lbl = tk.Label(nav, text="", bg=BG_MID, fg=TEXT_PRIMARY,
                                     font=("Helvetica", 12, "bold"))
        self.img_name_lbl.pack()

        self.pos_lbl = tk.Label(nav, text="", bg=BG_MID, fg=TEXT_MUTED,
                                font=("Helvetica", 9))
        self.pos_lbl.pack()

        grid = tk.Frame(nav, bg=BG_MID)
        grid.pack(pady=(8, 2))
        self._actions_grid = grid

        mk = self._btn
        self._nav_btns = {}

        b_pf = mk(grid, GLYPHS["prev2"], self.prev_folder,
                  bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10, width=5)
        self._shortcut_btns["prev_folder"] = (b_pf, GLYPHS["prev2"])
        b_pi = mk(grid, GLYPHS["prev"], self.prev_image,
                  bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10, width=5)
        self._shortcut_btns["prev_image"] = (b_pi, GLYPHS["prev"])

        self.keep_btn = mk(grid, f"{GLYPHS['keep']}  KEEP", self.act_keep,
                           bg=BTN_KEEP, hover=BTN_KEEP_HOV, width=12)
        self._shortcut_btns["keep"] = (self.keep_btn, f"{GLYPHS['keep']}  KEEP")
        self.del_btn = mk(grid, f"{GLYPHS['delete']}  DELETE", self.act_delete,
                          bg=BTN_DEL, hover=BTN_DEL_HOV, width=12)
        self._shortcut_btns["delete"] = (self.del_btn,
                                         f"{GLYPHS['delete']}  DELETE")
        self.note_btn = mk(grid, "Note", self.edit_note,
                           image=icon("edit-document"),
                           bg=BTN_NAV, hover=BTN_NAV_HOV, width=12)
        self.flag_btn = mk(grid, "Flag", self.toggle_flag, image=icon("flag"),
                           bg=BTN_NAV, hover=BTN_NAV_HOV, width=12)
        self._shortcut_btns["flag"] = (self.flag_btn, "")

        b_ni = mk(grid, GLYPHS["next"], self.next_image,
                  bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10, width=5)
        self._shortcut_btns["next_image"] = (b_ni, GLYPHS["next"])
        b_nf = mk(grid, GLYPHS["next2"], self.next_folder,
                  bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10, width=5)
        self._shortcut_btns["next_folder"] = (b_nf, GLYPHS["next2"])

        self._nav_btns = dict(pf=b_pf, pi=b_pi, keep=self.keep_btn,
                              dele=self.del_btn, note=self.note_btn,
                              flag=self.flag_btn, ni=b_ni, nf=b_nf)
        self._action_rows = None
        self._layout_actions(one_row=True)

        self.note_lbl = tk.Label(nav, text="", bg=BG_MID, fg=FLAG_TEXT,
                                 font=("Helvetica", 9))
        self.note_lbl.pack()

        self.state_lbl = tk.Label(nav, text="", bg=BG_MID,
                                  font=("Helvetica", 11, "bold"))
        self.state_lbl.pack()

        self.nav_mode_btn = self._btn(nav, "", self.toggle_nav_mode,
                                      bg=BTN_KEYS, hover=BTN_KEYS_HOV,
                                      font_size=8)
        self.nav_mode_btn.pack(pady=(5, 0))
        self._shortcut_btns["nav_mode"] = (self.nav_mode_btn, "")

    # Generous gaps so the groups read as groups rather than one long run
    GAP_GROUP = 18
    GAP_BTN = 5

    def _layout_actions(self, one_row):
        """(Re)place the marking buttons in one row or two."""
        if self._action_rows == one_row:
            return
        self._action_rows = one_row
        b = self._nav_btns
        for w in b.values():
            w.grid_forget()

        G, P = self.GAP_GROUP, self.GAP_BTN
        if one_row:
            order = [("pf", (0, G, P)), ("pi", (1, P, G)),
                     ("keep", (2, P, P)), ("dele", (3, P, P)),
                     ("note", (4, P, P)), ("flag", (5, P, G)),
                     ("ni", (6, G, P)), ("nf", (7, P, G))]
            for key, (col, lpad, rpad) in order:
                b[key].grid(row=0, column=col, padx=(lpad, rpad), pady=3,
                            sticky="ew")
        else:
            cells = [("pf", 0, 0), ("pi", 1, 0),
                     ("keep", 0, 1), ("dele", 0, 2),
                     ("note", 1, 1), ("flag", 1, 2),
                     ("nf", 0, 3), ("ni", 1, 3)]
            for key, row, col in cells:
                lpad = G if col == 1 else P
                rpad = G if col == 2 else P
                b[key].grid(row=row, column=col, padx=(lpad, rpad), pady=3,
                            sticky="ew")

    # ── Status bar ───────────────────────────────────────────────────────────
    def _build_statusbar(self):
        self.status_lbl = tk.Label(
            self.root, text="Open a directory to begin  •  K = Keep  •  D = Delete  •  ←/→ Navigate",
            bg=BG_MID, fg=TEXT_MUTED, anchor=tk.W, padx=12, pady=4,
            font=("Helvetica", 9),
        )
        self.status_lbl.pack(side=tk.BOTTOM, fill=tk.X)

    # ─── Widget factory ───────────────────────────────────────────────────────
    def _btn(self, parent, text, command, bg=BTN_NAV, hover=None, fg="white",
             font_size=10, width=None, state=tk.NORMAL, image=None):
        return FlatButton(parent, text=text, command=command,
                          bg=bg, hover=hover, fg=fg, image=image,
                          font_size=font_size, width=width, state=state)

    # ─── Action wrappers ──────────────────────────────────────────────────────
    # Named methods so ACTION_HANDLERS can resolve them by attribute name.
    def act_keep(self):
        self.set_state(True)

    def act_delete(self):
        self.set_state(False)

    # ─── Keyboard bindings ────────────────────────────────────────────────────
    def _bind_keys(self):
        """(Re)bind every action to its currently configured key."""
        # Clear anything bound previously so re-binding never stacks up
        for seq in self._bound_seqs:
            try:
                self.root.unbind(seq)
            except tk.TclError:
                pass
        self._bound_seqs = []

        for action_id, binding in self.bindings.items():
            handler_name = ACTION_HANDLERS.get(action_id)
            if not handler_name:
                continue
            handler = getattr(self, handler_name, None)
            if handler is None:
                continue
            for seq in binding_sequences(binding):
                try:
                    self.root.bind(seq, lambda e, h=handler: (h(), "break")[1])
                    self._bound_seqs.append(seq)
                except tk.TclError:
                    pass   # invalid sequence — skip rather than crash

    # Below this width the toolbar's full labels overflow, so they shorten.
    # Raised when the Export Notes button was added — at 1280px the full
    # label set pushed the stats readout off the edge.
    COMPACT_WIDTH = 1400

    def _apply_responsive(self, width=None):
        """Switch the toolbar between full and compact labels."""
        if width is None:
            width = self.root.winfo_width()
        compact = width < self.COMPACT_WIDTH
        if compact == getattr(self, "_compact", None):
            return
        self._compact = compact

        if hasattr(self, "keys_btn"):
            self.keys_btn.configure(
                text="" if compact else "Shortcuts")
        if hasattr(self, "export_btn"):
            self.export_btn.configure(
                text="Notes" if compact else "Export Notes")
        if hasattr(self, "zoom_hint"):
            self.zoom_hint.configure(
                text="" if compact else
                     "scroll to zoom  \u2022  drag to pan  \u2022  "
                     "double-click toggles fit / 1:1")
            if hasattr(self, "_zb_flow"):
                self._zb_flow.reflow()
        if hasattr(self, "stats_lbl"):
            self._update_stats()
        self._refresh_shortcut_labels()

    def _reflow_bars(self):
        for attr in ("_tb_flow", "_zb_flow", "_actions_flow", "_fs_flow"):
            bar = getattr(self, attr, None)
            if bar is not None:
                try:
                    bar.reflow()
                except Exception:
                    pass

    def _decide_action_rows(self):
        """
        Use one row whenever the buttons genuinely fit.

        Measuring beats a fixed breakpoint here: the button widths depend on
        the shortcut hints printed on them, which the user can rebind to
        anything from "K" to "Ctrl+Shift+F12".
        """
        grid = getattr(self, "_actions_grid", None)
        if grid is None or not self._nav_btns:
            return
        avail = self._viewer.winfo_width()
        if avail <= 1:
            return
        need = sum(w.winfo_reqwidth() for w in self._nav_btns.values())
        need += self.GAP_GROUP * 4 + self.GAP_BTN * 10
        self._layout_actions(one_row=need <= avail - 24)

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self._apply_responsive(event.width)
            self._decide_action_rows()

    def _refresh_shortcut_labels(self):
        """Append the current key to each button's label, e.g. '✓ KEEP [K]'."""
        compact = getattr(self, "_compact", False)
        compact_base = {
            "open_dir": "Open",
            "process":  f"{GLYPHS['process']}  Process",
        }
        for action_id, (btn, base_text) in self._shortcut_btns.items():
            if action_id in ("nav_mode", "preload", "note", "flag", "export_notes"):
                continue          # these manage their own variable labels
            if compact and action_id in compact_base:
                # Drop the key hint too — it's still shown in the Shortcuts dialog
                btn.configure(text=compact_base[action_id])
                continue
            key = self.bindings.get(action_id)
            btn.configure(text=f"{base_text}  [{display_binding(key)}]" if key else base_text)

        self._refresh_nav_mode_btn()
        self._refresh_preload_btn()
        self._refresh_note_ui()
        self._reflow_bars()
        self._decide_action_rows()

        # Status bar hint line
        if hasattr(self, "status_lbl"):
            self.status_lbl.config(text=(
                f"{display_binding(self.bindings['keep'])} = Keep  •  "
                f"{display_binding(self.bindings['delete'])} = Delete  •  "
                f"{display_binding(self.bindings['prev_image'])}/"
                f"{display_binding(self.bindings['next_image'])} = Navigate  •  "
                f"{display_binding(self.bindings['toggle'])} = Toggle  •  "
                "Click ⌨ Shortcuts to customise"
            ))

    # ─── Fullscreen ───────────────────────────────────────────────────────────
    def toggle_fullscreen(self):
        if getattr(self, "_fullscreen", False):
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def toggle_fs_size(self):
        """Switch between filling the display and filling the current window."""
        self.settings["fullscreen_mode"] = (
            "window" if self.settings.get("fullscreen_mode", "screen") == "screen"
            else "screen")
        save_config(self.bindings, self.settings)
        if getattr(self, "_fullscreen", False):
            self._apply_fs_size()
            self._refresh_fs_size_btn()
            self.root.after(80, lambda: self._render_view(recenter=True))
        else:
            self._refresh_fs_size_btn()

    def _apply_fs_size(self):
        want_screen = self.settings.get("fullscreen_mode", "screen") == "screen"
        try:
            self.root.attributes("-fullscreen", bool(want_screen))
        except tk.TclError:
            pass

    def _refresh_fs_size_btn(self):
        if not hasattr(self, "fs_size_btn") or self.fs_size_btn is None:
            return
        screen = self.settings.get("fullscreen_mode", "screen") == "screen"
        self.fs_size_btn.configure(
            text="Screen size" if screen else "Window size",
            bg=BTN_KEYS if screen else BTN_NAV,
            hover=BTN_KEYS_HOV if screen else BTN_NAV_HOV)

    def enter_fullscreen(self):
        """Hide the panels and give the image the whole area, keeping a
        compact strip of view controls so the mode stays usable."""
        if getattr(self, "_fullscreen", False) or self._src_img is None:
            return
        self._fullscreen = True

        try:
            self._saved_sash = self._pane.sash_coord(0)[0]
        except Exception:
            self._saved_sash = None

        for w in (self._toolbar, self._header, self._zbar,
                  self._nav, self.status_lbl, self._view_tb):
            try:
                w.pack_forget()
            except Exception:
                pass
        try:
            self._pane.forget(self._sidebar)
        except Exception:
            pass

        self._apply_fs_size()
        self._build_fs_bar()
        self.root.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.root.after(60, lambda: self._render_view(recenter=True))

    def _build_fs_bar(self):
        """Compact control strip shown only in fullscreen."""
        bar = tk.Frame(self.root, bg=BG_MID)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._fs_hint = bar

        flow = FlowBar(bar, bg=BG_MID, hgap=6, pady=5)
        flow.pack(fill=tk.X, padx=10)
        self._fs_flow = flow

        self.fs_name_lbl = tk.Label(flow, text="", bg=BG_MID, fg=TEXT_PRIMARY,
                                    font=("Helvetica", 10, "bold"))
        flow.add(self.fs_name_lbl, "left")

        def keyed(parent, action, **btn_kw):
            """
            Build a button with its shortcut printed underneath.

            The button is created directly inside the caption cell. Creating
            it against the outer frame and re-parenting with pack(in_=...)
            left the buttons unrendered, with only the captions visible.
            """
            cell = tk.Frame(parent, bg=BG_MID)
            w = self._btn(cell, **btn_kw)
            w.pack()
            key = self.bindings.get(action) if action else None
            tk.Label(cell, text=display_binding(key) if key else " ",
                     bg=BG_MID, fg=TEXT_MUTED,
                     font=("Helvetica", 7, "bold")).pack(pady=(1, 0))
            return cell, w

        nav = tk.Frame(flow, bg=BG_MID)
        for txt, cmd, act in ((GLYPHS["prev"], self.prev_image, "prev_image"),
                              (GLYPHS["next"], self.next_image, "next_image")):
            cell, _ = keyed(nav, act, text=txt, command=cmd,
                            bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=9)
            cell.pack(side=tk.LEFT, padx=4)
        flow.add(nav, "left")

        mark = tk.Frame(flow, bg=BG_MID)
        cell, self.fs_keep_btn = keyed(mark, "keep", text=GLYPHS["keep"],
                                       command=self.act_keep, bg=BTN_KEEP,
                                       hover=BTN_KEEP_HOV, font_size=9)
        cell.pack(side=tk.LEFT, padx=4)
        cell, self.fs_del_btn = keyed(mark, "delete", text=GLYPHS["delete"],
                                      command=self.act_delete, bg=BTN_DEL,
                                      hover=BTN_DEL_HOV, font_size=9)
        cell.pack(side=tk.LEFT, padx=4)
        cell, self.fs_flag_btn = keyed(mark, "flag", text="",
                                       command=self.toggle_flag,
                                       image=icon("flag"), bg=BTN_NAV,
                                       hover=BTN_NAV_HOV, font_size=9)
        cell.pack(side=tk.LEFT, padx=4)
        flow.add(mark, "left")

        # View operations — the reason fullscreen was awkward before
        view = tk.Frame(flow, bg=BG_MID)
        for ic, cmd, act in (("undo", self.rotate_ccw, "rot_ccw"),
                             ("redo", self.rotate_cw, "rot_cw"),
                             ("flip-horizontal", self.flip_horizontal, "flip_h"),
                             ("flip-vertical", self.flip_vertical, "flip_v")):
            cell, _ = keyed(view, act, text="", command=cmd, image=icon(ic),
                            bg=BTN_NAV, hover=BTN_NAV_HOV)
            cell.pack(side=tk.LEFT, padx=4)
        flow.add(view, "left")

        zoom = tk.Frame(flow, bg=BG_MID)
        cell, _ = keyed(zoom, "zoom_out", text="", command=self.zoom_out,
                        image=icon("collapse"), bg=BTN_NAV, hover=BTN_NAV_HOV)
        cell.pack(side=tk.LEFT, padx=4)
        self.fs_zoom_lbl = tk.Label(zoom, text="Fit", bg=BG_MID, fg=TEXT_PRIMARY,
                                    font=("Helvetica", 9, "bold"), width=6)
        self.fs_zoom_lbl.pack(side=tk.LEFT, padx=4)
        cell, _ = keyed(zoom, "zoom_in", text="", command=self.zoom_in,
                        image=icon("expand"), bg=BTN_NAV, hover=BTN_NAV_HOV)
        cell.pack(side=tk.LEFT, padx=4)
        cell, _ = keyed(zoom, "zoom_fit", text="Fit", command=self.zoom_fit,
                        bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=9)
        cell.pack(side=tk.LEFT, padx=4)
        cell, _ = keyed(zoom, "zoom_100", text="1:1", command=self.zoom_actual,
                        bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=9)
        cell.pack(side=tk.LEFT, padx=4)
        flow.add(zoom, "left")

        self.fs_size_btn = self._btn(flow, "", self.toggle_fs_size,
                                     bg=BTN_KEYS, hover=BTN_KEYS_HOV, font_size=9)
        flow.add(self.fs_size_btn, "right")
        self._refresh_fs_size_btn()

        flow.add(self._btn(flow, f"{GLYPHS['clear']}  Exit  [Esc]",
                           self.exit_fullscreen, bg=BTN_INVERT,
                           hover="#606878", font_size=9), "right")
        self._refresh_fs_labels()

    def _refresh_fs_labels(self):
        if not getattr(self, "_fullscreen", False):
            return
        fp = self._cur_file()
        if fp and hasattr(self, "fs_name_lbl"):
            files = self._cur_files()
            folder = rel(os.path.dirname(fp), self.base_dir)
            self.fs_name_lbl.config(
                text=f"{os.path.basename(fp)}   "
                     f"{self.cur_image_idx + 1}/{len(files)}   \u2022   {folder}")
        state = self.image_states.get(fp, True) if fp else True
        if hasattr(self, "fs_keep_btn"):
            self.fs_keep_btn.configure(bg=BTN_KEEP_HOV if state else "#0d4a22")
            self.fs_del_btn.configure(bg="#6b1111" if state else BTN_DEL_HOV)
        if hasattr(self, "fs_flag_btn"):
            flagged = bool(fp) and fp in self.notes
            self.fs_flag_btn.configure(
                bg=FLAG_ON if flagged else BTN_NAV,
                hover=FLAG_ON_HOV if flagged else BTN_NAV_HOV)
        if hasattr(self, "fs_zoom_lbl"):
            self.fs_zoom_lbl.config(text=self.zoom_lbl.cget("text"))

    def exit_fullscreen(self):
        if not getattr(self, "_fullscreen", False):
            return
        self._fullscreen = False
        try:
            self.root.attributes("-fullscreen", False)
        except tk.TclError:
            pass
        if getattr(self, "_fs_hint", None) is not None:
            self._fs_hint.destroy()
            self._fs_hint = None
        self.fs_size_btn = None
        self.root.unbind("<Escape>")

        self._toolbar.pack(side=tk.TOP, fill=tk.X, before=self._pane)
        try:
            self._pane.add(self._sidebar, minsize=170, stretch="never",
                           before=self._pane.panes()[0])
        except Exception:
            self._pane.add(self._sidebar, minsize=170, stretch="never")
        self._header.pack(side=tk.TOP, fill=tk.X, before=self.canvas)
        self._zbar.pack(side=tk.TOP, fill=tk.X, before=self.canvas)
        self._nav.pack(side=tk.BOTTOM, fill=tk.X, before=self.canvas)
        self._view_tb.pack(side=tk.LEFT, fill=tk.Y, before=self.canvas)
        self.status_lbl.pack(side=tk.BOTTOM, fill=tk.X)

        if self._saved_sash:
            try:
                self._pane.sash_place(0, self._saved_sash, 0)
            except Exception:
                pass
        self.root.after(60, lambda: self._render_view(recenter=True))
        self._refresh_shortcut_labels()

    # ─── Help ─────────────────────────────────────────────────────────────────
    def open_help(self):
        HelpDialog(self)

    # ─── Shutdown ─────────────────────────────────────────────────────────────
    def on_close(self):
        """Confirm before quitting, warning about notes that were never exported."""
        choice = ExitDialog(self).result
        if choice == "cancel":
            return
        if choice == "export":
            self.export_notes()
            # The save dialog can be cancelled; if the notes still aren't
            # written, stay open rather than quitting out from under them.
            if not self.notes_exported:
                return
        self._force_quit()

    def _force_quit(self):
        """
        Tear down in a safe order.

        ImageTk.PhotoImage finalisers call into the Tk interpreter. If those
        objects are still alive when root.destroy() runs, Python collects them
        afterwards and the C finaliser touches a destroyed interpreter — an
        intermittent segfault inside PIL._imagingtk with no Python traceback.
        Dropping every image reference first means the finalisers run while
        the interpreter is still valid.
        """
        self._stop_preload()
        for job in ("_resize_job", "_quality_job", "_pan_job"):
            jid = getattr(self, job, None)
            if jid:
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
                setattr(self, job, None)

        # Release image references while Tk is still alive
        self._photo = None
        self._src_img = None
        self._mip = None
        self._mip_src = None
        self._logo_img = None
        self._wordmark_img = None
        try:
            self._cache.clear()
        except Exception:
            pass
        _RRECT_CACHE.clear()
        _ICON_CACHE.clear()
        try:
            self.root._icon_ref = None
        except Exception:
            pass

        import gc
        gc.collect()          # force finalisers to run now, not post-destroy

        self.root.destroy()

    # ─── Flags & notes ────────────────────────────────────────────────────────
    NOTES_FILENAME = ".vismanager_notes.json"

    def _notes_path(self):
        if not self.base_dir:
            return None
        return os.path.join(self.base_dir, self.NOTES_FILENAME)

    def load_notes(self):
        """
        Read the sidecar note file for the current root.

        Notes live beside the assets rather than in the user profile so they
        travel with the folder — move the directory to another machine and
        the annotations come along. Paths are stored relative to the root for
        the same reason.
        """
        self.notes = {}
        self.transforms = {}
        p = self._notes_path()
        if not p or not os.path.exists(p):
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            for relpath, note in (data.get("notes") or {}).items():
                if isinstance(note, str):
                    self.notes[os.path.normpath(
                        os.path.join(self.base_dir, relpath))] = note
            for relpath, tr in (data.get("transforms") or {}).items():
                try:
                    rot, mirror = int(tr[0]) % 4, bool(tr[1])
                except (TypeError, ValueError, IndexError):
                    continue
                if rot or mirror:
                    self.transforms[os.path.normpath(
                        os.path.join(self.base_dir, relpath))] = (rot, mirror)
        except (json.JSONDecodeError, OSError):
            pass

    def save_notes(self):
        p = self._notes_path()
        if not p:
            return
        try:
            if not self.notes and not self.transforms:
                if os.path.exists(p):
                    os.remove(p)       # don't leave an empty file behind
                return
            payload = {
                "app": APP_NAME,
                "root": self.base_dir,
                "notes": {rel(k, self.base_dir).replace(os.sep, "/"): v
                          for k, v in sorted(self.notes.items())},
                "transforms": {rel(k, self.base_dir).replace(os.sep, "/"):
                               [r, m] for k, (r, m) in sorted(self.transforms.items())},
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def is_flagged(self, path):
        return path in self.notes

    def toggle_flag(self):
        """Flag/unflag without opening the editor. Keeps any existing text."""
        fp = self._cur_file()
        if not fp:
            return
        if fp in self.notes:
            del self.notes[fp]
        else:
            self.notes[fp] = ""
        self.save_notes()
        self._after_note_change()

    def set_note(self, path, text):
        text = (text or "").strip()
        if text:
            self.notes[path] = text
        else:
            self.notes.pop(path, None)     # empty note clears the flag
        self.save_notes()
        self._after_note_change()

    def edit_note(self):
        fp = self._cur_file()
        if fp:
            NoteDialog(self, fp)

    def _after_note_change(self):
        self.notes_exported = False        # export is now out of date
        self._refresh_note_ui()
        self._refresh_fs_labels()
        self._refresh_folder_lb()
        self._update_stats()

    def _refresh_note_ui(self):
        """Update the note button and the inline note preview."""
        fp = self._cur_file()
        flagged = bool(fp) and fp in self.notes
        note = self.notes.get(fp, "") if fp else ""

        if hasattr(self, "note_btn"):
            key = self.bindings.get("note")
            label = "Note"
            self.note_btn.configure(
                text=f"{label}  [{display_binding(key)}]" if key else label,
                bg=FLAG_ON if flagged else BTN_NAV,
                hover=FLAG_ON_HOV if flagged else BTN_NAV_HOV)

        if hasattr(self, "flag_btn"):
            fkey = self.bindings.get("flag")
            flabel = "Flagged" if flagged else "Flag"
            self.flag_btn.configure(
                text=f"{flabel}  [{display_binding(fkey)}]" if fkey else flabel,
                bg=FLAG_ON if flagged else BTN_NAV,
                hover=FLAG_ON_HOV if flagged else BTN_NAV_HOV)

        if hasattr(self, "note_lbl"):
            if note:
                one_line = " ".join(note.split())
                shown = one_line if len(one_line) <= 90 else one_line[:89] + "\u2026"
                self.note_lbl.config(text=f"{GLYPHS['flag_on']}  {shown}",
                                     fg=FLAG_TEXT)
            elif flagged:
                self.note_lbl.config(text=f"{GLYPHS['flag_on']}  flagged (no note)",
                                     fg=FLAG_TEXT)
            else:
                self.note_lbl.config(text="")

    def export_notes(self):
        """Write every flagged file and its note to a plain text report."""
        if not self.notes:
            messagebox.showinfo(
                "No Notes",
                "Nothing is flagged yet.\n\n"
                f"Press {display_binding(self.bindings.get('note'))} to add a note "
                f"or {display_binding(self.bindings.get('flag'))} to flag the "
                "current file.")
            return

        default_dir = self.base_dir or os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title="Export notes",
            defaultextension=".txt",
            initialdir=default_dir,
            initialfile="vismanager_notes.txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._build_notes_report())
        except OSError as exc:
            messagebox.showerror("Export Failed", f"Could not write the file:\n{exc}")
            return

        self.notes_exported = True
        self.last_export_path = path
        messagebox.showinfo(
            "Notes Exported",
            f"{len(self.notes)} flagged file(s) written to:\n\n{path}")

    def _build_notes_report(self):
        """Plain-text report, grouped by folder, in scan order."""
        import datetime

        lines = []
        lines.append(f"{APP_NAME} \u2014 flagged files report")
        lines.append("=" * 60)
        lines.append(f"Generated : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
        lines.append(f"Root      : {self.base_dir}")
        lines.append(f"Flagged   : {len(self.notes)} file(s)")
        lines.append("")

        # Group by folder, preserving the order the folders were scanned in.
        # Flagged files that have since been filtered out of view are still
        # reported — hiding a file type should not silently drop its notes.
        by_folder = {}
        for p in self.notes:
            by_folder.setdefault(os.path.dirname(p), []).append(p)

        ordered = [f for f in self.folder_list if f in by_folder]
        ordered += [f for f in sorted(by_folder) if f not in ordered]

        for folder in ordered:
            label = rel(folder, self.base_dir) if self.base_dir else folder
            lines.append(f"[{label}]")
            lines.append("-" * 60)
            for p in sorted(by_folder[folder]):
                mark = self.image_states.get(p)
                status = ("KEEP" if mark is True
                          else "DELETE" if mark is False else "not in view")
                lines.append(f"  {os.path.basename(p)}  ({status})")
                note = self.notes.get(p, "")
                if note:
                    for nl in note.splitlines():
                        lines.append(f"      {nl}")
                else:
                    lines.append("      (flagged, no note)")
                lines.append("")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"



    # ─── Cube (3D) support ────────────────────────────────────────────────────
    def _cube_scene(self, path):
        """
        Get (or build) the 3D scene for a cube file.

        One scene is kept at a time: each holds a VTK render window and the
        triangulated isosurfaces, which is far too much memory to cache per
        file across a directory of hundreds.
        """
        if not CUBE_SUPPORT:
            return None
        if getattr(self, "_scene_path", None) == path and self._scene is not None:
            return self._scene
        if self._scene is not None:
            self._scene.close()
            self._scene = None
        try:
            self._scene = cube_viewer.CubeScene(path, bg=self._cube_bg())
            self._scene_path = path
            self._scene_error = ""
        except Exception as exc:
            self._scene = None
            self._scene_path = None
            self._scene_error = str(exc)
        return self._scene

    def _cube_bg(self):
        c = KEEP_BG if self.image_states.get(self._cur_file(), True) else DELETE_BG
        return tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def is_cube_view(self):
        fp = self._cur_file()
        return bool(fp) and type_of(fp) == "cube" and self._scene is not None

    def _render_cube(self, fp):
        """Render the current cube to a PIL image sized to the canvas."""
        scene = self._cube_scene(fp)
        if scene is None:
            return None
        cw, ch = self._canvas_size()
        scene.renderer.SetBackground(*self._cube_bg())
        try:
            return scene.render(cw, ch)
        except Exception as exc:
            self._scene_error = str(exc)
            return None

    def cube_rotate(self, dx, dy):
        if self.is_cube_view():
            self._scene.rotate(dx, dy)
            self._show_image(keep_zoom=True, recenter=True)

    def cube_zoom(self, factor):
        if self.is_cube_view():
            self._scene.zoom(factor)
            self._show_image(keep_zoom=True, recenter=True)

    def cube_reset(self):
        if self.is_cube_view():
            self._scene.reset_camera()
            self._show_image(keep_zoom=True, recenter=True)

    def open_cube_export(self):
        if self.is_cube_view():
            CubeExportDialog(self, self._scene)
        elif CUBE_SUPPORT:
            messagebox.showinfo("Not a cube file",
                                "Open a .cube file to use 3D export.")

    def open_cube_settings(self):
        if self.is_cube_view():
            CubeSettingsDialog(self, self._scene)

    # ─── Orientation ──────────────────────────────────────────────────────────
    def get_transform(self, path):
        return self.transforms.get(path, (0, False))

    def _apply_op(self, op):
        fp = self._cur_file()
        if not fp:
            return
        rot, mirror = compose_transform(*self.get_transform(fp), op)
        if rot or mirror:
            self.transforms[fp] = (rot, mirror)
        else:
            self.transforms.pop(fp, None)      # identity isn't worth storing
        self.save_notes()
        # Zoom is kept: rotating while inspecting a detail shouldn't yank the
        # view back to fit. Recentre only, since the aspect may have swapped.
        self._show_image(keep_zoom=True, recenter=True)

    def rotate_cw(self):        self._apply_op("cw")
    def rotate_ccw(self):       self._apply_op("ccw")
    def flip_horizontal(self):  self._apply_op("h")
    def flip_vertical(self):    self._apply_op("v")
    def reset_transform(self):  self._apply_op("reset")

    def _refresh_cube_section(self):
        """Show the 3D controls only when they apply."""
        sec = getattr(self, "_cube_sec", None)
        if sec is None:
            return
        want = self.is_cube_view()
        if want and not sec.winfo_ismapped():
            sec.pack(fill=tk.X)
        elif not want and sec.winfo_ismapped():
            sec.pack_forget()

    def _refresh_transform_ui(self):
        fp = self._cur_file()
        rot, mirror = self.get_transform(fp) if fp else (0, False)
        if hasattr(self, "rot_lbl"):
            txt = transform_label(rot, mirror)
            self.rot_lbl.config(text=txt or "\u2014",
                                fg=FLAG_TEXT if txt else TEXT_MUTED)

    # ─── Shortcuts dialog ─────────────────────────────────────────────────────
    def open_shortcuts_dialog(self):
        ShortcutsDialog(self)

    def suspend_shortcuts(self):
        """
        Detach every app shortcut from root.  Called while the shortcuts
        dialog is open so that pressing 'd' to REBIND it can never also
        trigger the DELETE action, regardless of where keyboard focus sits.
        """
        for seq in self._bound_seqs:
            try:
                self.root.unbind(seq)
            except tk.TclError:
                pass
        self._bound_seqs = []

    def resume_shortcuts(self):
        """Re-attach app shortcuts after the dialog closes."""
        self._bind_keys()

    def apply_bindings(self, new_bindings):
        """Called by the dialog when the user saves."""
        self.bindings = dict(new_bindings)
        save_config(self.bindings, self.settings)
        self._bind_keys()
        self._refresh_shortcut_labels()

    # ─── Directory scanning ───────────────────────────────────────────────────
    def browse_directory(self):
        d = filedialog.askdirectory(title="Select root directory containing images")
        if d:
            self.base_dir = d
            self.dir_lbl.config(text=os.path.basename(d) or d)
            self.scan_directory()

    def scan_directory(self, preserve_states=False):
        """
        Walk the tree once, caching every supported file, then apply the
        active type filter.  Re-filtering later never touches the disk.
        """
        old_states = dict(self.image_states) if preserve_states else {}

        self._stop_preload()
        self._cache.clear()           # paths may have been deleted on disk
        self._all_files = []          # every supported file found on disk
        self.type_counts = {}         # {type_id: count} across the whole tree

        for root_dir, dirs, files in os.walk(self.base_dir):
            dirs.sort()
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in ALL_EXTS:
                    fp = os.path.join(root_dir, f)
                    self._all_files.append(fp)
                    tid = EXT_TO_TYPE[ext]
                    self.type_counts[tid] = self.type_counts.get(tid, 0) + 1

        self._rebuild_folders(old_states)
        self._build_type_filter_rows()

    def _rebuild_folders(self, old_states=None):
        """Group the cached scan into folders, honouring the type filter."""
        old_states = old_states if old_states is not None else dict(self.image_states)
        enabled = set(self.settings["enabled_types"])

        self.folder_list.clear()
        self.folders.clear()
        self.image_states.clear()

        by_folder = {}
        for fp in self._all_files:
            if type_of(fp) not in enabled:
                continue
            by_folder.setdefault(os.path.dirname(fp), []).append(fp)

        for folder in sorted(by_folder):
            files = sorted(by_folder[folder])
            self.folder_list.append(folder)
            self.folders[folder] = files
            for fp in files:
                self.image_states[fp] = old_states.get(fp, True)

        if not self.folder_list:
            self._show_empty_state()
            return

        self.cur_folder_idx = min(self.cur_folder_idx, len(self.folder_list) - 1)
        self.cur_image_idx  = min(self.cur_image_idx,
                                  max(0, len(self._cur_files()) - 1))

        self._refresh_folder_lb()
        self.process_btn.config(state=tk.NORMAL)
        self._show_image()
        self._update_stats()
        self._start_preload()

    def _show_empty_state(self):
        found = sum(self.type_counts.values()) if self.type_counts else 0
        msg = ("No supported files found in this directory."
               if found == 0 else
               "No files match the current type filter.")
        self.big_pos_lbl.config(text="—", fg=TEXT_MUTED)
        self.big_ctx_lbl.config(text=msg)
        self.prog_canvas.delete("all")
        self.canvas.delete("all")
        self.canvas.config(bg=BG_DARK)
        self.img_name_lbl.config(text="")
        self.pos_lbl.config(text="")
        self.state_lbl.config(text="")
        self.folder_lb.delete(0, tk.END)
        self.process_btn.config(state=tk.DISABLED)
        self._update_stats()

    def toggle_type(self, type_id):
        """Include/exclude a file type, keeping existing keep/delete marks."""
        enabled = set(self.settings["enabled_types"])
        if type_id in enabled:
            enabled.discard(type_id)
        else:
            enabled.add(type_id)
        self.settings["enabled_types"] = [t for t in ALL_TYPE_IDS if t in enabled]
        save_config(self.bindings, self.settings)
        self._rebuild_folders()
        self._build_type_filter_rows()

    # ─── Current helpers ──────────────────────────────────────────────────────
    def _cur_files(self):
        if not self.folder_list:
            return []
        return self.folders.get(self.folder_list[self.cur_folder_idx], [])

    def _cur_file(self):
        files = self._cur_files()
        if files and 0 <= self.cur_image_idx < len(files):
            return files[self.cur_image_idx]
        return None

    # ─── Image display ────────────────────────────────────────────────────────
    # ─── Preload / cache ──────────────────────────────────────────────────────
    def toggle_preload(self):
        mode = self.settings.get("preload_mode", "lazy")
        self.settings["preload_mode"] = "lazy" if mode == "folder" else "folder"
        save_config(self.bindings, self.settings)
        self._refresh_preload_btn()
        if self.settings["preload_mode"] == "folder":
            self._start_preload()
        else:
            self._stop_preload()
        self._update_cache_label()

    def _refresh_preload_btn(self):
        if not hasattr(self, "preload_btn"):
            return
        lazy = self.settings.get("preload_mode") == "lazy"
        base = "One at a time" if lazy else "Whole folder"
        self._shortcut_btns["preload"] = (self.preload_btn, base)
        key = self.bindings.get("preload")
        # A single sheet for one-at-a-time, a stack for whole-folder — the
        # icon says which mode is active without reading the label.
        self.preload_btn.configure(
            text=f"{base}  [{display_binding(key)}]" if key else base,
            image=icon("file-single" if lazy else "files-stack"),
            bg=BTN_NAV if lazy else "#0e7490",
            hover=BTN_NAV_HOV if lazy else "#0891b2",
        )

    def _update_cache_label(self):
        if not hasattr(self, "cache_lbl"):
            return
        n, used, cap = self._cache.stats()
        self.cache_lbl.config(
            text=f"cached {n}  ({used:.0f}/{cap:.0f} MB)" if n else "")

    def _stop_preload(self):
        """Signal the worker to stop and tear down the polling loop."""
        if self._preload_stop is not None:
            self._preload_stop.set()
        if self._preload_job is not None:
            try:
                self.root.after_cancel(self._preload_job)
            except Exception:
                pass
            self._preload_job = None
        self._preload_thread = None
        self._preload_q = None
        self._hide_loading()

    def _start_preload(self):
        """Decode every uncached file in the current folder on a worker thread."""
        self._stop_preload()
        if self.settings.get("preload_mode") != "folder":
            return
        files = list(self._cur_files())
        todo = [f for f in files if not self._cache.has(f)]
        if not todo:
            self._update_cache_label()
            return

        stop = threading.Event()
        q = queue.Queue()
        self._preload_stop = stop
        self._preload_q = q
        self._preload_total = len(todo)
        self._preload_done = 0

        def worker(paths, stop_evt, out):
            # Decoding happens off the main thread so the UI stays responsive;
            # only plain data crosses the queue, never Tk objects.
            for p in paths:
                if stop_evt.is_set():
                    break
                try:
                    img, info = load_visual(p)
                except Exception as exc:
                    img, info = None, {"pages": None, "note": "", "error": str(exc)}
                out.put((p, img, info))
            out.put(None)

        self._preload_thread = threading.Thread(
            target=worker, args=(todo, stop, q), daemon=True)
        self._preload_thread.start()
        self._show_loading()
        self._preload_job = self.root.after(60, self._poll_preload)

    def _poll_preload(self):
        """Drain finished decodes into the cache. Runs on the main thread."""
        self._preload_job = None
        q = self._preload_q
        if q is None:
            return

        finished = False
        for _ in range(12):                 # bounded drain keeps the UI smooth
            try:
                item = q.get_nowait()
            except queue.Empty:
                break
            if item is None:
                finished = True
                break
            path, img, info = item
            self._cache.put(path, img, info)
            self._preload_done += 1

        self._show_loading()
        self._update_cache_label()

        if finished or (self._preload_stop and self._preload_stop.is_set()):
            self._hide_loading()
            self._preload_q = None
            self._preload_thread = None
            return
        self._preload_job = self.root.after(60, self._poll_preload)

    def _show_loading(self):
        if self._preload_total <= 0:
            return
        pct = self._preload_done / self._preload_total * 100
        folder = (rel(self.folder_list[self.cur_folder_idx], self.base_dir)
                  if self.folder_list else "")
        self.load_lbl.config(
            text=f"Loading {self._preload_done}/{self._preload_total}  \u2022  {folder}")
        self.load_bar["value"] = pct
        if not self.load_frame.winfo_ismapped():
            self.load_frame.pack(after=self.big_ctx_lbl, pady=(6, 0))

    def _hide_loading(self):
        if hasattr(self, "load_frame") and self.load_frame.winfo_ismapped():
            self.load_frame.pack_forget()
        self._preload_total = 0
        self._preload_done = 0

    def _load_cached(self, fp):
        """Cache-first load. Populates the cache in lazy mode too, so that
        stepping back and forth through a folder stays instant."""
        hit = self._cache.get(fp)
        if hit is not None:
            return hit
        img, info = load_visual(fp)
        self._cache.put(fp, img, info)
        return img, info

    def _show_image(self, keep_zoom=False, recenter=None):
        """Load the current file and draw it. Zoom resets unless keep_zoom."""
        fp = self._cur_file()
        if not fp:
            return

        if type_of(fp) == "cube":
            # Volumetric data is rendered live rather than decoded once, so it
            # bypasses the image cache entirely.
            img = self._render_cube(fp)
            if img is None:
                self._src_img = None
                self._draw_unloadable(fp, {"error": self._scene_error or
                                           "Install VTK for .cube support"})
                return
            info = {"pages": None, "note": "", "error": ""}
        else:
            img, info = self._load_cached(fp)
        if img is None:
            self._src_img = None
            self._draw_unloadable(fp, info)
            return

        # The cache holds the original decode; orientation is applied on the
        # way out, so rotating a file never invalidates its cached entry.
        rot, mirror = self.get_transform(fp)
        img = apply_transform(img, rot, mirror)

        self._cur_info = info
        self._src_img = img

        if not keep_zoom:
            self._zoom = 1.0          # back to fit on every new image

        self._render_view(
            recenter=(not keep_zoom) if recenter is None else recenter)
        self._update_labels(fp, img)
        self._refresh_note_ui()
        self._refresh_transform_ui()
        self._refresh_fs_labels()
        self._refresh_cube_section()

    # ─── Zoom / pan ───────────────────────────────────────────────────────────
    ZOOM_MIN, ZOOM_MAX = 0.1, 64.0        # multipliers on top of fit
    ZOOM_STEP = 1.25

    def _canvas_size(self):
        return (max(self.canvas.winfo_width(), 50),
                max(self.canvas.winfo_height(), 50))

    def _compute_fit(self):
        """Scale at which the image fits the canvas with a small margin."""
        if self._src_img is None:
            return 1.0
        cw, ch = self._canvas_size()
        pad = 20
        W, H = self._src_img.size
        return min((cw - pad) / W, (ch - pad) / H)

    def _clamp(self, cw, ch, dw, dh):
        """Centre the image when it is smaller than the canvas, else keep it
        from being dragged entirely out of view."""
        if dw <= cw:
            self._ox = (cw - dw) / 2
        else:
            self._ox = min(0.0, max(cw - dw, self._ox))
        if dh <= ch:
            self._oy = (ch - dh) / 2
        else:
            self._oy = min(0.0, max(ch - dh, self._oy))

    def _render_source(self, s):
        """
        Pick what to resize from, returning (image, scale_of_that_image).

        Shrinking a 4096px texture straight to canvas width means filtering
        16M pixels on every frame. Image.reduce() does a cheap integer box
        reduction once, and every later frame resamples the much smaller
        result. The mip is rebuilt only when the image or the required
        reduction factor changes.
        """
        img = self._src_img
        if img is None or s >= 0.5:
            return img, 1.0

        # Keep roughly 2x the pixels actually needed, so quality holds up
        want = int(1.0 / s / 2.0)
        factor = 1
        while factor * 2 <= want and factor < 16:
            factor *= 2
        if factor <= 1:
            return img, 1.0

        if self._mip_src is not img or self._mip_factor != factor:
            try:
                self._mip = img.reduce(factor)
            except Exception:
                self._mip, factor = img, 1
            self._mip_src = img
            self._mip_factor = factor
        return self._mip, 1.0 / self._mip_factor

    def _render_view(self, recenter=False, interactive=False):
        """
        Draw only the visible part of the image.

        Cropping to the viewport *before* resizing is what makes deep zoom
        safe: scaling a 4096px image to 32x would otherwise allocate a
        131072px-wide bitmap and exhaust memory. Cost here stays proportional
        to the canvas, not to the zoom level.

        `interactive` trades filter quality for latency while the user is
        actively dragging or spinning the wheel; a full-quality pass is
        scheduled once the gesture settles.
        """
        if self._src_img is None:
            return
        W, H = self._src_img.size
        cw, ch = self._canvas_size()

        self._fit_scale = self._compute_fit()
        s = self._fit_scale * self._zoom
        dw, dh = W * s, H * s

        if recenter:
            self._ox, self._oy = (cw - dw) / 2, (ch - dh) / 2
        self._clamp(cw, ch, dw, dh)

        fp = self._cur_file()
        state = self.image_states.get(fp, True)
        self.canvas.config(bg=KEEP_BG if state else DELETE_BG)
        # Draw the replacement first and remove the old items afterwards.
        # Clearing up front leaves one frame of empty canvas, which shows as
        # a visible blink on every zoom, pan and resize step.
        stale = self.canvas.find_all()

        src, src_scale = self._render_source(s)
        es = s / src_scale                 # src pixels -> screen pixels
        Ws, Hs = src.size

        # Visible rectangle, in the coordinate space of whichever source we use
        x0 = max(0, int(math.floor(-self._ox / es)))
        y0 = max(0, int(math.floor(-self._oy / es)))
        x1 = min(Ws, int(math.ceil((cw - self._ox) / es)))
        y1 = min(Hs, int(math.ceil((ch - self._oy) / es)))

        if x1 > x0 and y1 > y0:
            crop = src.crop((x0, y0, x1, y1))
            tw = max(1, int(round((x1 - x0) * es)))
            th = max(1, int(round((y1 - y0) * es)))
            if es >= 2.0:
                # Magnified: NEAREST keeps texels crisp, and it is the
                # fastest option anyway.
                resample = Image.NEAREST
            elif interactive:
                resample = Image.BILINEAR
            else:
                resample = Image.LANCZOS
            self._photo = ImageTk.PhotoImage(crop.resize((tw, th), resample))
            self.canvas.create_image(self._ox + x0 * es, self._oy + y0 * es,
                                     anchor=tk.NW, image=self._photo)

        for item in stale:
            self.canvas.delete(item)

        self._update_zoom_label(s)

        # Once the gesture stops, redraw properly filtered
        if self._quality_job:
            try:
                self.root.after_cancel(self._quality_job)
            except Exception:
                pass
            self._quality_job = None
        if interactive and es < 2.0:
            self._quality_job = self.root.after(130, self._render_quality)

    def _render_quality(self):
        self._quality_job = None
        if self._src_img is not None:
            self._render_view()

    def _update_zoom_label(self, s=None):
        if self._src_img is None:
            self.zoom_lbl.config(text="\u2014", fg=TEXT_MUTED)
            return
        if s is None:
            s = self._fit_scale * self._zoom
        txt = "Fit" if abs(self._zoom - 1.0) < 0.001 else f"{s * 100:.0f}%"
        self.zoom_lbl.config(
            text=txt,
            fg=TEXT_PRIMARY if abs(self._zoom - 1.0) < 0.001 else "#fbbf24")
        if getattr(self, "_fullscreen", False) and hasattr(self, "fs_zoom_lbl"):
            self.fs_zoom_lbl.config(text=txt)

    def _set_zoom(self, new_zoom, anchor=None, interactive=False):
        """Zoom to new_zoom, keeping the point under `anchor` (canvas x,y) put."""
        if self._src_img is None:
            return
        new_zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, new_zoom))
        if abs(new_zoom - self._zoom) < 1e-9:
            return

        old_s = self._fit_scale * self._zoom
        new_s = self._fit_scale * new_zoom
        if anchor is None:
            cw, ch = self._canvas_size()
            anchor = (cw / 2, ch / 2)
        ax, ay = anchor
        # Source coords under the anchor stay fixed across the zoom change
        sx = (ax - self._ox) / old_s
        sy = (ay - self._oy) / old_s
        self._zoom = new_zoom
        self._ox = ax - sx * new_s
        self._oy = ay - sy * new_s
        self._render_view(interactive=interactive)

    def zoom_in(self):
        self._set_zoom(self._zoom * self.ZOOM_STEP)

    def zoom_out(self):
        self._set_zoom(self._zoom / self.ZOOM_STEP)

    def zoom_fit(self):
        self._zoom = 1.0
        self._render_view(recenter=True)

    def zoom_actual(self):
        """1:1 — one image pixel per screen pixel."""
        if self._src_img is None:
            return
        self._fit_scale = self._compute_fit() or 1.0
        self._set_zoom(1.0 / self._fit_scale)

    def _on_wheel(self, event, force=None):
        delta = force if force is not None else event.delta
        if not delta:
            return "break"
        # macOS reports small deltas, Windows multiples of 120
        steps = delta / 120.0 if abs(delta) >= 120 else (1 if delta > 0 else -1)
        if self.is_cube_view():
            self.cube_zoom(1.12 if steps > 0 else 1 / 1.12)
            return "break"
        self._set_zoom(self._zoom * (self.ZOOM_STEP ** steps),
                       anchor=(event.x, event.y), interactive=True)
        return "break"

    def _on_pan_start(self, event):
        self._pan_from = (event.x, event.y, self._ox, self._oy)
        self._panned = False
        self.canvas.config(cursor="fleur")

    def _on_pan_move(self, event):
        if not self._pan_from or self._src_img is None:
            return
        x0, y0, ox0, oy0 = self._pan_from
        dx, dy = event.x - x0, event.y - y0
        if abs(dx) > 2 or abs(dy) > 2:
            self._panned = True
        if self.is_cube_view():
            # On a cube, dragging orbits the camera — panning a live render
            # would just move a picture that is about to be redrawn anyway.
            self._scene.rotate(event.x - x0, event.y - y0)
            self._pan_from = (event.x, event.y, self._ox, self._oy)
            if self._pan_job is None:
                self._pan_job = self.root.after_idle(self._flush_cube_drag)
            return
        self._ox, self._oy = ox0 + dx, oy0 + dy
        # Motion events arrive faster than we can redraw. Collapsing them
        # into one render per idle cycle keeps the drag tracking the cursor
        # instead of lagging behind a backlog of stale positions.
        if self._pan_job is None:
            self._pan_job = self.root.after_idle(self._flush_pan)

    def _flush_cube_drag(self):
        self._pan_job = None
        self._show_image(keep_zoom=True, recenter=True)

    def _flush_pan(self):
        self._pan_job = None
        self._render_view(interactive=True)

    def _on_pan_end(self, _event):
        self._pan_from = None
        if self._pan_job is not None:
            try:
                self.root.after_cancel(self._pan_job)
            except Exception:
                pass
            self._pan_job = None
        self._render_view()            # final full-quality pass
        self.canvas.config(cursor="crosshair")

    def _on_double_click(self, event):
        if abs(self._zoom - 1.0) < 0.001:
            self.zoom_actual()
        else:
            self.zoom_fit()
        return "break"

    def _update_labels(self, fp, img):
        files = self._cur_files()
        state = self.image_states.get(fp, True)
        folder_rel = rel(os.path.dirname(fp), self.base_dir)

        self.big_pos_lbl.config(
            text=f"{self.cur_image_idx + 1} / {len(files)}",
            fg=BTN_KEEP_HOV if state else BTN_DEL_HOV,
        )
        self.big_ctx_lbl.config(
            text=f"{folder_rel}   \u2022   folder "
                 f"{self.cur_folder_idx + 1} of {len(self.folder_list)}"
        )
        self._draw_progress()

        tid = type_of(fp)
        extra = ""
        pages = (getattr(self, "_cur_info", {}) or {}).get("pages")
        if pages and pages > 1:
            extra = f"  \u2502  {pages} pages"

        self.img_name_lbl.config(text=os.path.basename(fp))
        self.pos_lbl.config(
            text=f"Folder: {folder_rel}  \u2502  "
                 f"Image {self.cur_image_idx + 1} / {len(files)}  \u2502  "
                 f"Folder {self.cur_folder_idx + 1} / {len(self.folder_list)}  \u2502  "
                 f"{TYPE_LABELS.get(tid, '?')}  \u2502  "
                 f"{img.width} \u00d7 {img.height}{extra}"
        )
        self._update_state_indicator(state)
        self._refresh_folder_lb()

    def _draw_unloadable(self, fp, info):
        """
        Draw an informative card when a file can't be rendered — e.g. a PDF
        with no renderer installed.  The file is still fully reviewable:
        keep/delete marking works regardless of preview.
        """
        files = self._cur_files()
        state = self.image_states.get(fp, True)
        self.canvas.config(bg=KEEP_BG if state else DELETE_BG)
        self.canvas.delete("all")

        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 300)
        tid = type_of(fp)

        self.canvas.create_text(
            cw // 2, ch // 2 - 50, text=TYPE_LABELS.get(tid, "FILE"),
            fill=TEXT_MUTED, font=("Helvetica", 42, "bold"))
        self.canvas.create_text(
            cw // 2, ch // 2 + 4, text=os.path.basename(fp),
            fill=TEXT_PRIMARY, font=("Helvetica", 13, "bold"))
        self.canvas.create_text(
            cw // 2, ch // 2 + 44,
            text=info.get("error") or "No preview available",
            fill=BTN_DEL_HOV, font=("Helvetica", 10), width=cw - 80,
            justify=tk.CENTER)
        self.canvas.create_text(
            cw // 2, ch // 2 + 96,
            text="You can still mark this file Keep or Delete.",
            fill=TEXT_MUTED, font=("Helvetica", 9))

        folder_rel = rel(os.path.dirname(fp), self.base_dir)
        self.big_pos_lbl.config(
            text=f"{self.cur_image_idx + 1} / {len(files)}",
            fg=BTN_KEEP_HOV if state else BTN_DEL_HOV)
        self.big_ctx_lbl.config(
            text=f"{folder_rel}   •   folder "
                 f"{self.cur_folder_idx + 1} of {len(self.folder_list)}")
        self._draw_progress()
        self.img_name_lbl.config(text=os.path.basename(fp))
        self.pos_lbl.config(
            text=f"Folder: {folder_rel}  │  "
                 f"Image {self.cur_image_idx + 1} / {len(files)}  │  "
                 f"{TYPE_LABELS.get(tid, '?')}  │  no preview")
        self._update_state_indicator(state)
        self._refresh_note_ui()
        self._refresh_transform_ui()
        self._refresh_folder_lb()
        self._update_zoom_label()

    def _draw_progress(self):
        """Thin bar under the big counter: how far through this folder we are."""
        if not hasattr(self, "prog_canvas"):
            return
        self.prog_canvas.delete("all")
        files = self._cur_files()
        if not files:
            return
        w = self.prog_canvas.winfo_width()
        if w <= 1:
            return
        frac = (self.cur_image_idx + 1) / len(files)
        state = self.image_states.get(self._cur_file(), True)
        self.prog_canvas.create_rectangle(
            0, 0, w * frac, 4,
            fill=BTN_KEEP_HOV if state else BTN_DEL_HOV, width=0,
        )

    def _update_state_indicator(self, state: bool):
        if state:
            # KEEP is active: bright green keep, dim red delete
            self.state_lbl.config(text=f"{GLYPHS['dot']} KEEP", fg=BTN_KEEP_HOV, bg=BG_MID)
            self.keep_btn.config(bg=BTN_KEEP_HOV)   # brightest shade = "active"
            self.del_btn.config( bg="#6b1111")       # heavily dimmed = "inactive"
        else:
            # DELETE is active: dim green keep, bright red delete
            self.state_lbl.config(text=f"{GLYPHS['dot']} DELETE", fg=BTN_DEL_HOV, bg=BG_MID)
            self.keep_btn.config(bg="#0d4a22")       # heavily dimmed = "inactive"
            self.del_btn.config( bg=BTN_DEL_HOV)     # brightest shade = "active"

    # ─── Navigation ───────────────────────────────────────────────────────────
    def toggle_nav_mode(self):
        self.settings["nav_mode"] = (
            "wrap" if self.settings["nav_mode"] == "continuous" else "continuous"
        )
        save_config(self.bindings, self.settings)
        self._refresh_nav_mode_btn()
        self._refresh_preload_btn()
        self._refresh_note_ui()

    def _refresh_nav_mode_btn(self):
        if not hasattr(self, "nav_mode_btn"):
            return
        wrap = self.settings["nav_mode"] == "wrap"
        base = (f"{GLYPHS['wrap']}  Wrap in folder" if wrap
                else f"{GLYPHS['cont']}  Continuous (all folders)")
        self._shortcut_btns["nav_mode"] = (self.nav_mode_btn, base)
        key = self.bindings.get("nav_mode")
        self.nav_mode_btn.configure(
            text=f"{base}  [{display_binding(key)}]" if key else base,
            bg="#7c3aed" if wrap else BTN_KEYS,
            hover="#8b5cf6" if wrap else BTN_KEYS_HOV,
        )

    def next_image(self):
        """
        Continuous : run off the end of a folder into the next folder,
                     and from the last folder back round to the first.
        Wrap       : stay inside the current folder, looping to its start.
        """
        files = self._cur_files()
        if not files:
            return

        if self.cur_image_idx < len(files) - 1:
            self.cur_image_idx += 1
            self._show_image()
            return

        if self.settings["nav_mode"] == "wrap":
            self.cur_image_idx = 0            # loop within this folder
            self._show_image()
        else:
            if self.cur_folder_idx < len(self.folder_list) - 1:
                self.cur_folder_idx += 1
            else:
                self.cur_folder_idx = 0       # wrap round the whole set
            self.cur_image_idx = 0
            self._sync_folder_lb()
            self._show_image()
            self._start_preload()

    def prev_image(self):
        files = self._cur_files()
        if not files:
            return

        if self.cur_image_idx > 0:
            self.cur_image_idx -= 1
            self._show_image()
            return

        if self.settings["nav_mode"] == "wrap":
            self.cur_image_idx = len(files) - 1
            self._show_image()
        else:
            if self.cur_folder_idx > 0:
                self.cur_folder_idx -= 1
            else:
                self.cur_folder_idx = len(self.folder_list) - 1
            self.cur_image_idx = max(0, len(self._cur_files()) - 1)
            self._sync_folder_lb()
            self._show_image()
            self._start_preload()

    def next_folder(self):
        if not self.folder_list:
            return
        self.cur_folder_idx = (self.cur_folder_idx + 1) % len(self.folder_list)
        self.cur_image_idx  = 0
        self._sync_folder_lb()
        self._show_image()
        self._start_preload()

    def prev_folder(self, go_to_last=False):
        if not self.folder_list:
            return
        self.cur_folder_idx = (self.cur_folder_idx - 1) % len(self.folder_list)
        self.cur_image_idx  = (len(self._cur_files()) - 1) if go_to_last else 0
        self.cur_image_idx  = max(0, self.cur_image_idx)
        self._sync_folder_lb()
        self._show_image()
        self._start_preload()

    def _on_folder_select(self, _event=None):
        sel = self.folder_lb.curselection()
        if sel:
            self.cur_folder_idx = sel[0]
            self.cur_image_idx  = 0
            self._show_image()
            self._start_preload()

    def _on_canvas_resize(self, _event=None):
        """
        Keep the image tracking the window while it is being dragged.

        Waiting for the resize to settle left the canvas showing a stale
        image for 120ms and then snapping to the new size — with white-page
        documents that reads as a flash. An interactive render costs only a
        few milliseconds, so the picture can follow the edge continuously;
        the sharp pass still happens once the drag stops.
        """
        if self._src_img is not None and self._resize_paint_job is None:
            self._resize_paint_job = self.root.after_idle(self._resize_paint)
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(140, self._on_resize_done)

    def _resize_paint(self):
        self._resize_paint_job = None
        if self._src_img is not None:
            self._render_view(recenter=abs(self._zoom - 1.0) < 0.001,
                              interactive=True)

    def _on_resize_done(self):
        self._resize_job = None
        if self._src_img is not None:
            self._render_view(recenter=abs(self._zoom - 1.0) < 0.001)
        else:
            self._show_image()

    # ─── State management ─────────────────────────────────────────────────────
    def set_state(self, keep: bool):
        fp = self._cur_file()
        if fp:
            self.image_states[fp] = keep
            # keep_zoom: marking an image must not throw away the user's
            # zoom/pan — they are often zoomed in to judge it.
            self._show_image(keep_zoom=True)
            self._update_stats()

    def toggle_state(self):
        fp = self._cur_file()
        if fp:
            self.set_state(not self.image_states.get(fp, True))

    def keep_all_folder(self):
        self._set_folder_state(True)

    def delete_all_folder(self):
        self._set_folder_state(False)

    def invert_folder(self):
        files = self._cur_files()
        for f in files:
            self.image_states[f] = not self.image_states.get(f, True)
        self._show_image()
        self._update_stats()

    def _set_folder_state(self, keep: bool):
        for f in self._cur_files():
            self.image_states[f] = keep
        self._show_image()
        self._update_stats()

    def _build_type_filter_rows(self):
        """One toggle per file type actually present in the scanned tree."""
        if not hasattr(self, "type_filter_frame"):
            return
        for w in self.type_filter_frame.winfo_children():
            w.destroy()
        self._type_rows.clear()

        present = [t for t in ALL_TYPE_IDS if self.type_counts.get(t)]
        if not present:
            tk.Label(self.type_filter_frame, text="  (none found)",
                     bg=BG_SIDEBAR, fg=TEXT_MUTED,
                     font=("Helvetica", 9)).pack(anchor=tk.W)
            return

        enabled = set(self.settings["enabled_types"])
        for tid in present:
            on  = tid in enabled
            cnt = self.type_counts[tid]
            row = FlatButton(
                self.type_filter_frame,
                text=f"{GLYPHS['checked'] if on else GLYPHS['unchecked']}  {TYPE_LABELS[tid]:<5} {cnt}",
                command=lambda t=tid: self.toggle_type(t),
                bg="#2f4858" if on else "#33333f",
                hover="#3d5b70" if on else "#3f3f4d",
                font_size=9,
            )
            row.pack(fill=tk.X, pady=1)
            self._type_rows[tid] = row

        # All / None helpers
        btns = tk.Frame(self.type_filter_frame, bg=BG_SIDEBAR)
        btns.pack(fill=tk.X, pady=(4, 0))
        FlatButton(btns, text="All", command=lambda: self._set_all_types(True),
                   bg=BTN_INVERT, hover="#606878", font_size=8).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        FlatButton(btns, text="None", command=lambda: self._set_all_types(False),
                   bg=BTN_INVERT, hover="#606878", font_size=8).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # Make a missing/degraded PDF backend visible rather than mysterious
        if self.type_counts.get("pdf"):
            backend = _resolve_pdf_backend()
            if backend == "none":
                txt, col = f"{GLYPHS['warn']} no PDF preview", BTN_DEL_HOV
            elif backend == "pypdf":
                txt, col = "PDF: embedded-image mode", "#fbbf24"
            else:
                txt, col = f"PDF: {backend}", TEXT_MUTED
            tk.Label(self.type_filter_frame, text=txt, bg=BG_SIDEBAR, fg=col,
                     font=("Helvetica", 8)).pack(anchor=tk.W, pady=(4, 0))

    def _set_all_types(self, on):
        present = [t for t in ALL_TYPE_IDS if self.type_counts.get(t)]
        enabled = set(self.settings["enabled_types"])
        for t in present:
            enabled.add(t) if on else enabled.discard(t)
        self.settings["enabled_types"] = [t for t in ALL_TYPE_IDS if t in enabled]
        save_config(self.bindings, self.settings)
        self._rebuild_folders()
        self._build_type_filter_rows()

    # ─── Sidebar refresh ──────────────────────────────────────────────────────
    def _refresh_folder_lb(self):
        self.folder_lb.delete(0, tk.END)
        for fp in self.folder_list:
            files      = self.folders[fp]
            keep_n     = sum(1 for f in files if self.image_states.get(f, True))
            label      = rel(fp, self.base_dir)
            flag_n     = sum(1 for f in files if f in self.notes)
            flag_txt   = f"  {GLYPHS['flag_on']}{flag_n}" if flag_n else ""
            entry_text = f"{label}  ({keep_n}/{len(files)} \u2713){flag_txt}"
            self.folder_lb.insert(tk.END, entry_text)
        self._sync_folder_lb()

    def _sync_folder_lb(self):
        self.folder_lb.select_clear(0, tk.END)
        self.folder_lb.select_set(self.cur_folder_idx)
        self.folder_lb.see(self.cur_folder_idx)

    # ─── Stats ────────────────────────────────────────────────────────────────
    def _update_stats(self):
        total  = len(self.image_states)
        keep_n = sum(1 for v in self.image_states.values() if v)
        del_n  = total - keep_n
        compact = getattr(self, "_compact", False)

        if not hasattr(self, "keep_stat"):
            return
        if total == 0:
            for w in (self.keep_stat, self.del_stat,
                      self.flag_stat, self.total_stat):
                w.config(text="")
            return

        self.keep_stat.config(text=f"{GLYPHS['keep']} {keep_n}"
                              if compact else f"Keep {keep_n}")
        self.del_stat.config(text=f"{GLYPHS['delete']} {del_n}"
                             if compact else f"Delete {del_n}")
        self.flag_stat.config(
            text=(f"{GLYPHS['flag_on']} {len(self.notes)}") if self.notes else "")
        self.total_stat.config(text=f"of {total}")
        self._reflow_bars()

    # ─── Processing ───────────────────────────────────────────────────────────
    @staticmethod
    def _flatten(img):
        """Composite transparency over white and return an RGB image."""
        if img.mode in ("RGBA", "LA", "P"):
            if img.mode == "P":
                img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
            bg.paste(img, mask=mask)
            return bg
        return img.convert("RGB")

    @staticmethod
    def _unique_pdf_path(src, used, protected):
        """
        Pick a PDF path that clobbers nothing.

        'a/logo.tga' and 'a/logo.png' both want 'a/logo.pdf', so on collision
        the source type is folded into the name — logo_tga.pdf, logo_png.pdf —
        and a counter is added if even that is taken.  'protected' holds paths
        we must never overwrite (e.g. PDFs already in the review set).
        """
        stem = os.path.splitext(src)[0]
        ext  = os.path.splitext(src)[1].lstrip(".").lower()

        candidates = [f"{stem}.pdf", f"{stem}_{ext}.pdf"]
        candidates += [f"{stem}_{ext}_{i}.pdf" for i in range(2, 100)]

        for cand in candidates:
            if cand in used or cand in protected:
                continue
            if os.path.exists(cand) and cand not in used:
                continue          # don't silently replace an unrelated file
            return cand
        return f"{stem}_{ext}_{os.getpid()}.pdf"

    def process_images(self):
        if not self.image_states:
            messagebox.showwarning("Nothing to Process", "No files loaded.")
            return

        keep_files   = [f for f, k in self.image_states.items() if k]
        delete_files = [f for f, k in self.image_states.items() if not k]

        if not keep_files and not delete_files:
            messagebox.showinfo("Nothing to do", "No files are marked.")
            return

        dlg = ProcessOptionsDialog(self, keep_files, delete_files)
        opts = dlg.result
        if opts is None:
            return                                   # cancelled

        self.settings.update(opts)
        save_config(self.bindings, self.settings)

        plan = self._build_plan(keep_files, delete_files, opts)
        if not messagebox.askyesno(
                "Confirm Processing",
                "This will:\n\n" + "\n".join(plan["lines"]) + "\n\nContinue?",
                icon="warning" if plan["destructive"] else "question"):
            return

        self._do_process(plan, opts)

    def _build_plan(self, keep_files, delete_files, opts):
        """Work out exactly which files get converted and which get removed."""
        del_marked = opts["delete_marked_types"]
        del_source = opts["delete_source_types"]

        convertible = [f for f in keep_files if type_of(f) not in NON_CONVERTIBLE]
        skipped     = [f for f in keep_files if type_of(f) in NON_CONVERTIBLE]

        to_delete = [f for f in delete_files if del_marked.get(type_of(f), False)]
        spared    = [f for f in delete_files if not del_marked.get(type_of(f), False)]
        sources   = [f for f in convertible if del_source.get(type_of(f), False)]

        mode_txt = {
            "per_image":  "One PDF per file (saved beside each original)",
            "per_folder": "One PDF per folder",
            "combined":   "Single combined PDF",
        }[opts["pdf_mode"]]

        def by_type(files):
            counts = {}
            for f in files:
                t = type_of(f)
                counts[t] = counts.get(t, 0) + 1
            return ", ".join(f"{n} {TYPE_LABELS.get(t, t)}"
                             for t, n in sorted(counts.items()))

        lines = []
        if convertible:
            lines.append(f"  • Convert {len(convertible)} file(s) to PDF  "
                         f"({by_type(convertible)})")
            lines.append(f"      {mode_txt}")
        if skipped:
            lines.append(f"  • Skip {len(skipped)} PDF(s) — already PDF, not re-converted")
        if sources:
            lines.append(f"  • DELETE {len(sources)} source file(s) after converting  "
                         f"({by_type(sources)})")
        if to_delete:
            lines.append(f"  • DELETE {len(to_delete)} marked file(s)  ({by_type(to_delete)})")
        if spared:
            lines.append(f"  • Keep {len(spared)} marked file(s) — their type has "
                         f"deletion off  ({by_type(spared)})")
        if not lines:
            lines.append("  • Nothing — no types are enabled for conversion or deletion")

        return {
            "lines": lines,
            "destructive": bool(to_delete or sources),
            "convertible": convertible,
            "skipped": skipped,
            "to_delete": to_delete,
            "spared": spared,
            "sources": sources,
        }

    def _do_process(self, plan, opts):
        pdf_mode    = opts["pdf_mode"]
        convertible = plan["convertible"]
        to_delete   = plan["to_delete"]
        sources     = plan["sources"]

        # ── Progress window ──
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Processing…")
        prog_win.geometry("470x150")
        prog_win.transient(self.root)
        prog_win.grab_set()
        prog_win.resizable(False, False)
        prog_win.configure(bg=BG_MID)

        tk.Label(prog_win, text="Processing Files", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 12, "bold")).pack(pady=(16, 6))

        prog_var = tk.DoubleVar()
        ttk.Progressbar(prog_win, variable=prog_var, maximum=100,
                        length=390).pack(padx=30)
        prog_lbl = tk.Label(prog_win, text="", bg=BG_MID, fg=TEXT_MUTED,
                            font=("Helvetica", 9))
        prog_lbl.pack(pady=4)
        prog_win.update()

        errors, pdf_paths = [], []
        converted = 0
        total = max(1, len(convertible) + len(to_delete) + len(sources))
        done  = [0]

        def step(msg=""):
            done[0] += 1
            prog_var.set(done[0] / total * 100)
            prog_lbl.config(text=msg[:76])
            prog_win.update()

        def build_pdf(paths, pdf_path):
            nonlocal converted
            images = []
            for f in paths:
                step(f"Converting {os.path.basename(f)}")
                try:
                    img, _info = load_visual(f)
                    if img is None:
                        errors.append(f"Unreadable: {os.path.basename(f)}")
                        continue
                    # Carry the on-screen orientation into the output — a PDF
                    # that ignored the rotation you set would be a nasty
                    # surprise after a long review session.
                    rot, mirror = self.get_transform(f)
                    img = apply_transform(img, rot, mirror)
                    images.append(self._flatten(img))
                    converted += 1
                except Exception as exc:
                    errors.append(f"Load error {os.path.basename(f)}: {exc}")
            if not images:
                return False
            try:
                images[0].save(pdf_path, "PDF", resolution=100.0,
                               save_all=True, append_images=images[1:])
                pdf_paths.append(pdf_path)
                return True
            except Exception as exc:
                errors.append(f"PDF save error {os.path.basename(pdf_path)}: {exc}")
                return False

        # Never overwrite a file that is itself part of the review set
        protected = set(self.image_states)
        used = set()

        # ── Convert ──
        if pdf_mode == "per_image":
            for f in sorted(convertible):
                out = self._unique_pdf_path(f, used, protected)
                used.add(out)
                build_pdf([f], out)

        elif pdf_mode == "per_folder":
            by_folder = {}
            for f in convertible:
                by_folder.setdefault(os.path.dirname(f), []).append(f)
            for folder, files in sorted(by_folder.items()):
                name = os.path.basename(folder) or "root"
                out  = os.path.join(folder, f"{name}_images.pdf")
                build_pdf(sorted(files), out)

        elif convertible:
            build_pdf(sorted(convertible),
                      os.path.join(self.base_dir, "combined_images.pdf"))

        # ── Delete converted sources ──
        removed_sources = 0
        for f in sources:
            step(f"Removing source {os.path.basename(f)}")
            try:
                os.remove(f)
                removed_sources += 1
            except Exception as exc:
                errors.append(f"Delete error {os.path.basename(f)}: {exc}")

        # ── Delete marked files (only for types with deletion enabled) ──
        deleted = 0
        for f in to_delete:
            step(f"Deleting {os.path.basename(f)}")
            try:
                os.remove(f)
                deleted += 1
            except Exception as exc:
                errors.append(f"Delete error {os.path.basename(f)}: {exc}")

        prog_win.destroy()

        # ── Summary ──
        parts = [f"  ✓ Converted {converted} file(s) into {len(pdf_paths)} PDF(s)"]
        if plan["skipped"]:
            parts.append(f"  • Skipped {len(plan['skipped'])} existing PDF(s)")
        if sources:
            parts.append(f"  ✓ Removed {removed_sources} source file(s)")
        parts.append(f"  ✓ Deleted {deleted} marked file(s)")
        if plan["spared"]:
            parts.append(f"  • Spared {len(plan['spared'])} marked file(s) "
                         f"— deletion off for their type")

        if len(pdf_paths) <= 8:
            pdf_list = "\n".join(f"  • {rel(p, self.base_dir)}" for p in pdf_paths)
        else:
            shown = "\n".join(f"  • {rel(p, self.base_dir)}" for p in pdf_paths[:8])
            pdf_list = f"{shown}\n  … and {len(pdf_paths) - 8} more"

        msg = "Done!\n\n" + "\n".join(parts) + \
              (f"\n\nPDF(s) saved:\n{pdf_list}" if pdf_paths else "")
        if errors:
            msg += f"\n\n{GLYPHS['warn']} {len(errors)} error(s):\n" + "\n".join(errors[:6])

        messagebox.showinfo("Processing Complete", msg)

        if self.base_dir and os.path.isdir(self.base_dir):
            self.scan_directory(preserve_states=True)


# ─── Note editor ──────────────────────────────────────────────────────────────
class NoteDialog(tk.Toplevel):
    """
    Multi-line note editor for a single file.

    App shortcuts are suspended for the lifetime of this dialog. Without that,
    typing "d" in the note box would also mark the image for deletion, since
    the single-key bindings live on the root window.
    """

    def __init__(self, app, path):
        super().__init__(app.root)
        self.app  = app
        self.path = path
        self._closed = False

        app.suspend_shortcuts()

        self.title("Note")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(True, True)
        self.minsize(460, 280)

        self._build()

        self.update_idletasks()
        px, py = app.root.winfo_rootx(), app.root.winfo_rooty()
        pw, ph = app.root.winfo_width(), app.root.winfo_height()
        w, h   = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{max(20, py + (ph - h) // 3)}")

        self.grab_set()
        self.focus_force()
        self.txt.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        # Ctrl+Enter saves; plain Enter inserts a newline like any text box
        self.bind("<Control-Return>", lambda e: self._save())

    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, padx=18, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"{GLYPHS['note']}  Note", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 13, "bold")).pack(anchor=tk.W)
        tk.Label(hdr, text=os.path.basename(self.path), bg=BG_MID, fg=FLAG_TEXT,
                 font=("Helvetica", 10)).pack(anchor=tk.W)
        folder = (rel(os.path.dirname(self.path), self.app.base_dir)
                  if self.app.base_dir else os.path.dirname(self.path))
        tk.Label(hdr, text=folder, bg=BG_MID, fg=TEXT_MUTED,
                 font=("Helvetica", 8)).pack(anchor=tk.W)

        body = tk.Frame(self, bg=BG_DARK, padx=18, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        self.txt = tk.Text(
            body, height=7, wrap=tk.WORD,
            bg=BG_MID, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
            selectbackground=ACCENT_BLUE, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT_BLUE, font=("Helvetica", 10), padx=8, pady=6,
        )
        self.txt.pack(fill=tk.BOTH, expand=True)
        existing = self.app.notes.get(self.path, "")
        if existing:
            self.txt.insert("1.0", existing)

        tk.Label(body, text="Ctrl+Enter saves  \u2022  Esc cancels  \u2022  "
                            "an empty note removes the flag",
                 bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 8)).pack(anchor=tk.W, pady=(6, 0))

        footer = tk.Frame(self, bg=BG_MID, padx=18, pady=10)
        footer.pack(fill=tk.X)
        FlatButton(footer, text="Save", command=self._save,
                   bg=BTN_KEEP, hover=BTN_KEEP_HOV,
                   font_size=10, width=8).pack(side=tk.RIGHT, padx=(6, 0))
        FlatButton(footer, text="Cancel", command=self._cancel,
                   bg=BG_DARK, hover="#3a3a55",
                   font_size=10, width=8).pack(side=tk.RIGHT)
        if self.path in self.app.notes:
            FlatButton(footer, text=f"{GLYPHS['clear']}  Remove flag",
                       command=self._remove, bg=BTN_DEL, hover=BTN_DEL_HOV,
                       font_size=9).pack(side=tk.LEFT)

    def _save(self):
        self.app.set_note(self.path, self.txt.get("1.0", tk.END))
        self._close()

    def _remove(self):
        self.app.set_note(self.path, "")
        self._close()

    def _cancel(self):
        self._close()

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


# ─── Process options dialog ───────────────────────────────────────────────────
class ProcessOptionsDialog(tk.Toplevel):
    """PDF granularity plus per-file-type deletion control."""

    def __init__(self, app, keep_files, delete_files):
        super().__init__(app.root)
        self.app    = app
        self.result = None

        # Which types are actually involved, and how many of each
        self.keep_counts, self.del_counts = {}, {}
        for f in keep_files:
            t = type_of(f); self.keep_counts[t] = self.keep_counts.get(t, 0) + 1
        for f in delete_files:
            t = type_of(f); self.del_counts[t] = self.del_counts.get(t, 0) + 1
        self.types_present = [t for t in ALL_TYPE_IDS
                              if t in self.keep_counts or t in self.del_counts]

        self.title("Process Options")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(True, True)
        self.minsize(560, 420)
        app.suspend_shortcuts()

        s = app.settings
        self.pdf_mode = tk.StringVar(value=s["pdf_mode"])
        self.v_marked = {t: tk.BooleanVar(
            value=s["delete_marked_types"].get(t, True)) for t in self.types_present}
        self.v_source = {t: tk.BooleanVar(
            value=s["delete_source_types"].get(t, False)) for t in self.types_present}

        self._build(len(keep_files), len(delete_files))

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.scroller.fit_content(max_height=int(sh * 0.55),
                                  max_width=sw - 120)
        self.update_idletasks()
        self.minsize(min(self.winfo_reqwidth(), sw - 60), 400)
        fit_to_screen(self)

        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_window()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self, n_keep, n_delete):
        hdr = tk.Frame(self, bg=BG_MID, padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Process Options", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(hdr, text=f"{n_keep} marked KEEP  •  {n_delete} marked DELETE",
                 bg=BG_MID, fg=TEXT_MUTED, font=("Helvetica", 9)).pack(anchor=tk.W)

        footer = tk.Frame(self, bg=BG_MID, padx=20, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        self._footer = footer

        scroller = ScrollFrame(self, bg=BG_DARK)
        scroller.pack(fill=tk.BOTH, expand=True, padx=(20, 6), pady=14)
        self.scroller = scroller
        body = scroller.body

        # ── PDF output ──
        tk.Label(body, text="PDF OUTPUT", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))

        for val, title, sub in [
            ("per_image",  "One PDF per file",
             "Each image becomes its own PDF, saved in the same folder"),
            ("per_folder", "One PDF per folder",
             "All kept images in a folder combined into that folder's PDF"),
            ("combined",   "Single combined PDF",
             "Every kept image in one PDF at the root directory"),
        ]:
            f = tk.Frame(body, bg=BG_DARK)
            f.pack(fill=tk.X, anchor=tk.W)
            tk.Radiobutton(
                f, text=title, value=val, variable=self.pdf_mode,
                bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_MID,
                activebackground=BG_DARK, activeforeground=TEXT_PRIMARY,
                highlightthickness=0, bd=0, font=("Helvetica", 10), anchor=tk.W,
            ).pack(anchor=tk.W)
            tk.Label(f, text=f"      {sub}", bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Helvetica", 8)).pack(anchor=tk.W, pady=(0, 4))

        if "pdf" in self.keep_counts:
            tk.Label(body,
                     text=f"      Note: {self.keep_counts['pdf']} kept PDF(s) are "
                          f"already PDFs and won't be re-converted.",
                     bg=BG_DARK, fg="#fbbf24",
                     font=("Helvetica", 8)).pack(anchor=tk.W)

        tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=12)

        # ── Per-type deletion grid ──
        tk.Label(body, text="DELETION BY FILE TYPE", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="Control each type independently. Leave a box "
                           "unchecked to protect that type.",
                 bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 8)).pack(anchor=tk.W, pady=(0, 6))

        grid = tk.Frame(body, bg=BG_DARK)
        grid.pack(fill=tk.X)

        tk.Label(grid, text="Type", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold"), width=10, anchor=tk.W
                 ).grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        tk.Label(grid, text="Delete marked", bg=BG_DARK, fg=BTN_DEL_HOV,
                 font=("Helvetica", 9, "bold"), width=16
                 ).grid(row=0, column=1, pady=(0, 4))
        tk.Label(grid, text="Delete source after PDF", bg=BG_DARK, fg="#fbbf24",
                 font=("Helvetica", 9, "bold"), width=22
                 ).grid(row=0, column=2, pady=(0, 4))

        for i, tid in enumerate(self.types_present, start=1):
            nk = self.keep_counts.get(tid, 0)
            nd = self.del_counts.get(tid, 0)
            tk.Label(grid, text=f"{TYPE_LABELS[tid]}", bg=BG_DARK, fg=TEXT_PRIMARY,
                     font=("Helvetica", 10, "bold"), anchor=tk.W, width=10
                     ).grid(row=i, column=0, sticky=tk.W)

            # Delete-marked column
            cell1 = tk.Frame(grid, bg=BG_DARK)
            cell1.grid(row=i, column=1)
            if nd:
                tk.Checkbutton(
                    cell1, text=f"{nd}", variable=self.v_marked[tid],
                    bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_MID,
                    activebackground=BG_DARK, activeforeground=TEXT_PRIMARY,
                    highlightthickness=0, bd=0, font=("Helvetica", 10),
                ).pack()
            else:
                tk.Label(cell1, text="—", bg=BG_DARK, fg="#4a4a66",
                         font=("Helvetica", 10)).pack()

            # Delete-source column (never offered for PDFs — nothing is made from them)
            cell2 = tk.Frame(grid, bg=BG_DARK)
            cell2.grid(row=i, column=2)
            if nk and tid not in NON_CONVERTIBLE:
                tk.Checkbutton(
                    cell2, text=f"{nk}", variable=self.v_source[tid],
                    bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_MID,
                    activebackground=BG_DARK, activeforeground=TEXT_PRIMARY,
                    highlightthickness=0, bd=0, font=("Helvetica", 10),
                ).pack()
            else:
                tk.Label(cell2, text="—", bg=BG_DARK, fg="#4a4a66",
                         font=("Helvetica", 10)).pack()

        # Bulk helpers
        bulk = tk.Frame(body, bg=BG_DARK)
        bulk.pack(fill=tk.X, pady=(10, 0))
        FlatButton(bulk, text="Check all marked",
                   command=lambda: self._set_col(self.v_marked, True),
                   bg=BTN_INVERT, hover="#606878", font_size=8).pack(side=tk.LEFT, padx=(0, 4))
        FlatButton(bulk, text="Uncheck all marked",
                   command=lambda: self._set_col(self.v_marked, False),
                   bg=BTN_INVERT, hover="#606878", font_size=8).pack(side=tk.LEFT, padx=4)
        FlatButton(bulk, text="Uncheck all sources",
                   command=lambda: self._set_col(self.v_source, False),
                   bg=BTN_INVERT, hover="#606878", font_size=8).pack(side=tk.LEFT, padx=4)

        scroller.bind_wheel_recursive()

        footer = self._footer
        FlatButton(footer, text="Run", command=self._ok,
                   bg=BTN_PROCESS, hover=BTN_PROCESS_HOV,
                   font_size=10, width=8).pack(side=tk.RIGHT, padx=(6, 0))
        FlatButton(footer, text="Cancel", command=self._cancel,
                   bg=BG_DARK, hover="#3a3a55",
                   font_size=10, width=8).pack(side=tk.RIGHT)

    def _set_col(self, varmap, value):
        for v in varmap.values():
            v.set(value)

    # ── Result ───────────────────────────────────────────────────────────────
    def _ok(self):
        marked = dict(self.app.settings["delete_marked_types"])
        source = dict(self.app.settings["delete_source_types"])
        marked.update({t: v.get() for t, v in self.v_marked.items()})
        source.update({t: v.get() for t, v in self.v_source.items()})
        self.result = {
            "pdf_mode":            self.pdf_mode.get(),
            "delete_marked_types": marked,
            "delete_source_types": source,
        }
        self._close()

    def _cancel(self):
        self.result = None
        self._close()

    def _close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


# ─── Shortcuts dialog ─────────────────────────────────────────────────────────
class ShortcutsDialog(tk.Toplevel):
    """
    Modal editor for every keyboard shortcut.

    Capture is focus-proof: while the dialog is open the app's own shortcuts
    are suspended entirely, and the capture listener is attached with
    bind_all().  That means a keypress is recorded no matter which widget
    holds focus, and can never double-fire the underlying app action.
    """

    def __init__(self, app):
        super().__init__(app.root)
        self.app     = app
        self.working = dict(app.bindings)     # edit a copy; commit on Save
        self.capturing_action = None
        self.key_btns   = {}
        self.row_frames = {}
        self._blink_job = None
        self._blink_on  = False
        self._closed    = False

        # Silence the app's shortcuts for the lifetime of this dialog
        app.suspend_shortcuts()

        self.title("Keyboard Shortcuts")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(True, True)
        self.minsize(640, 380)

        self._build()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.scroller.fit_content(max_height=int(sh * 0.55),
                                  max_width=sw - 120)
        self.update_idletasks()
        self.minsize(min(self.winfo_reqwidth(), sw - 60), 360)
        fit_to_screen(self)

        self.grab_set()
        self.focus_force()                    # take real keyboard focus
        self.bind("<Escape>", self._on_escape)
        self.protocol("WM_DELETE_WINDOW", self.close)

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, pady=12, padx=18)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Keyboard Shortcuts", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(hdr, text="Click a shortcut, then press the key you want.",
                 bg=BG_MID, fg=TEXT_MUTED, font=("Helvetica", 9)).pack(anchor=tk.W)

        # Prominent listening banner — hidden until capture starts
        self.banner = tk.Label(self, text="", bg=CAPTURE_BG, fg="#ffffff",
                               font=("Helvetica", 11, "bold"), pady=8)

        # Footer and hint are packed BEFORE the scrolling body. Pack gives
        # earlier children their space first, so Save and Cancel stay pinned
        # to the bottom however long the action list grows.
        footer = tk.Frame(self, bg=BG_MID, pady=10, padx=18)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        self.hint = tk.Label(self, text="", bg=BG_DARK, fg="#fbbf24",
                             font=("Helvetica", 9, "bold"))
        self.hint.pack(side=tk.BOTTOM, pady=(0, 6))

        scroller = ScrollFrame(self, bg=BG_DARK)
        scroller.pack(fill=tk.BOTH, expand=True, padx=(18, 6), pady=12)
        self.scroller = scroller
        body = scroller.body

        # Two columns: 26 actions in a single stack is taller than most
        # screens. Splitting halves the height and keeps the list scannable.
        # Two columns unless the screen is too narrow to show both, in which
        # case one column plus scrolling beats clipping the right-hand side.
        two_col = self.winfo_screenwidth() >= 900
        per_col = ((len(ACTIONS) + 1) // 2) if two_col else len(ACTIONS)
        cols = [tk.Frame(body, bg=BG_DARK)]
        cols[0].grid(row=0, column=0, sticky="nw")
        body.grid_columnconfigure(0, weight=1)
        if two_col:
            cols.append(tk.Frame(body, bg=BG_DARK))
            cols[1].grid(row=0, column=1, sticky="nw", padx=(24, 0))
            body.grid_columnconfigure(1, weight=1)

        for i, (action_id, label, _default, _h) in enumerate(ACTIONS):
            parent = cols[0] if i < per_col else cols[1]
            row = tk.Frame(parent, bg=BG_DARK)
            row.pack(fill=tk.X, pady=3)
            self.row_frames[action_id] = row

            lbl = tk.Label(row, text=label, bg=BG_DARK, fg=TEXT_PRIMARY,
                           font=("Helvetica", 10), anchor=tk.W, width=20)
            lbl.pack(side=tk.LEFT)
            row.name_lbl = lbl

            btn = FlatButton(
                row, text=display_binding(self.working[action_id]),
                command=lambda a=action_id: self._start_capture(a),
                bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10, width=12,
            )
            btn.pack(side=tk.LEFT, padx=6)
            self.key_btns[action_id] = btn

            FlatButton(row, text=GLYPHS['clear'],
                       command=lambda a=action_id: self._clear(a),
                       bg="#4b5563", hover="#6b7280", font_size=8).pack(side=tk.LEFT)

        scroller.bind_wheel_recursive()
        FlatButton(footer, text="Reset to Defaults", command=self._reset,
                   bg=BTN_INVERT, hover="#606878", font_size=9).pack(side=tk.LEFT)
        FlatButton(footer, text="Save", command=self._save,
                   bg=BTN_KEEP, hover=BTN_KEEP_HOV, font_size=10,
                   width=8).pack(side=tk.RIGHT, padx=(6, 0))
        FlatButton(footer, text="Cancel", command=self.close,
                   bg=BG_DARK, hover="#3a3a55", font_size=10,
                   width=8).pack(side=tk.RIGHT)

    # ── Capture ──────────────────────────────────────────────────────────────
    def _start_capture(self, action_id):
        if self.capturing_action == action_id:
            self._end_capture()               # clicking again cancels
            return
        if self.capturing_action:
            self._end_capture()

        self.capturing_action = action_id

        # Show the banner
        self.banner.config(
            text=f"{GLYPHS['dot']}  LISTENING — press a key for “{ACTION_LABELS[action_id]}”"
                 f"      (Esc to cancel)")
        self.banner.pack(fill=tk.X, after=self.winfo_children()[0])

        # Dim every other row so the active one stands out
        for aid, btn in self.key_btns.items():
            if aid == action_id:
                continue
            btn.configure(bg="#2f2f45", hover="#2f2f45")
            self.row_frames[aid].name_lbl.config(fg="#5a5a78")

        self.row_frames[action_id].name_lbl.config(fg="#fbbf24")
        self.hint.config(text="Waiting for keypress…")
        self._start_blink()

        # bind_all → caught regardless of which widget has focus.
        # Safe because app shortcuts are suspended while this dialog lives.
        self.bind_all("<KeyPress>", self._on_capture_key)
        self.focus_force()

    def _start_blink(self):
        self._blink_on = not self._blink_on
        aid = self.capturing_action
        if aid:
            btn = self.key_btns[aid]
            if self._blink_on:
                btn.configure(text=f"{GLYPHS['dot']}  Press a key\u2026", bg=CAPTURE_BG, hover=CAPTURE_BG)
                self.banner.config(bg=CAPTURE_BG)
            else:
                btn.configure(text=f"{GLYPHS['dot_o']}  Press a key\u2026", bg="#a16207", hover="#a16207")
                self.banner.config(bg="#a16207")
            self._blink_job = self.after(450, self._start_blink)

    def _stop_blink(self):
        if self._blink_job:
            try:
                self.after_cancel(self._blink_job)
            except Exception:
                pass
            self._blink_job = None
        self._blink_on = False

    def _on_capture_key(self, event):
        if not self.capturing_action:
            return "break"
        if event.keysym == "Escape":
            self._end_capture()
            self.hint.config(text="Cancelled — shortcut unchanged")
            return "break"

        binding = event_to_binding(event)
        if binding is None:                   # bare modifier — keep waiting
            return "break"

        action_id = self.capturing_action
        note = ""

        # Conflict: clear whoever held this key before
        for other, b in list(self.working.items()):
            if other != action_id and b == binding:
                self.working[other] = ""
                self.key_btns[other].configure(text="—")
                note = (f"'{display_binding(binding)}' taken from "
                        f"“{ACTION_LABELS[other]}”")

        self.working[action_id] = binding
        self._end_capture()
        self.hint.config(
            text=note or f"“{ACTION_LABELS[action_id]}” → {display_binding(binding)}")
        return "break"

    def _end_capture(self):
        self._stop_blink()
        try:
            self.unbind_all("<KeyPress>")
        except tk.TclError:
            pass

        self.banner.pack_forget()

        # Restore every row to its normal appearance
        for aid, btn in self.key_btns.items():
            btn.configure(text=display_binding(self.working[aid]),
                          bg=BTN_NAV, hover=BTN_NAV_HOV)
            self.row_frames[aid].name_lbl.config(fg=TEXT_PRIMARY)

        self.capturing_action = None

    def _on_escape(self, _e=None):
        if self.capturing_action:
            self._end_capture()
            self.hint.config(text="Cancelled — shortcut unchanged")
        else:
            self.close()
        return "break"

    # ── Actions ──────────────────────────────────────────────────────────────
    def _clear(self, action_id):
        if self.capturing_action:
            self._end_capture()
        self.working[action_id] = ""
        self.key_btns[action_id].configure(text="—")
        self.hint.config(text=f"“{ACTION_LABELS[action_id]}” now has no shortcut")

    def _reset(self):
        if self.capturing_action:
            self._end_capture()
        self.working = dict(DEFAULT_BINDINGS)
        for aid, btn in self.key_btns.items():
            btn.configure(text=display_binding(self.working[aid]),
                          bg=BTN_NAV, hover=BTN_NAV_HOV)
        self.hint.config(text="Restored default shortcuts")

    def _save(self):
        if self.capturing_action:
            self._end_capture()
        self.app.apply_bindings(self.working)
        self.close(resume=False)              # apply_bindings already rebound

    # ── Teardown ─────────────────────────────────────────────────────────────
    def close(self, resume=True):
        """Single exit path — always releases grab and restores shortcuts."""
        if self._closed:
            return
        self._closed = True
        self._stop_blink()
        try:
            self.unbind_all("<KeyPress>")
        except tk.TclError:
            pass
        try:
            self.grab_release()
        except tk.TclError:
            pass
        if resume:
            self.app.resume_shortcuts()
        self.destroy()


# ─── Cube 3D dialogs ──────────────────────────────────────────────────────────
class CubeSettingsDialog(tk.Toplevel):
    """Isosurface controls for the current cube file."""

    def __init__(self, app, scene):
        super().__init__(app.root)
        self.app, self.scene = app, scene
        self._closed = False
        app.suspend_shortcuts()

        self.title("Isosurface")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(False, False)
        self._build()
        fit_to_screen(self)
        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, padx=18, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Isosurface", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 13, "bold")).pack(anchor=tk.W)
        lo, hi = self.scene.data_range
        tk.Label(hdr, text=f"{os.path.basename(self.scene.path)}   \u2022   "
                           f"grid {'x'.join(str(d) for d in self.scene.dimensions)}"
                           f"   \u2022   values {lo:.4f} to {hi:.4f}",
                 bg=BG_MID, fg=TEXT_MUTED, font=("Helvetica", 8)).pack(anchor=tk.W)

        body = tk.Frame(self, bg=BG_DARK, padx=18, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="ISOVALUE", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.iso_lbl = tk.Label(body, text="", bg=BG_DARK, fg=FLAG_TEXT,
                                font=("Helvetica", 11, "bold"))
        self.iso_lbl.pack(anchor=tk.W)

        top = max(self.scene.max_iso, 1e-6)
        self.iso = tk.DoubleVar(value=self.scene.isovalue)
        tk.Scale(body, from_=top * 0.002, to=top * 0.9, resolution=top / 500.0,
                 orient=tk.HORIZONTAL, variable=self.iso, showvalue=False,
                 length=300, bg=BG_DARK, fg=TEXT_PRIMARY, troughcolor=BG_MID,
                 highlightthickness=0, bd=0, activebackground=ACCENT_BLUE,
                 command=self._on_iso).pack(fill=tk.X, pady=(2, 10))

        tk.Label(body, text="OPACITY", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.op = tk.DoubleVar(value=self.scene.opacity)
        tk.Scale(body, from_=0.1, to=1.0, resolution=0.05,
                 orient=tk.HORIZONTAL, variable=self.op, showvalue=False,
                 length=300, bg=BG_DARK, fg=TEXT_PRIMARY, troughcolor=BG_MID,
                 highlightthickness=0, bd=0, activebackground=ACCENT_BLUE,
                 command=self._on_opacity).pack(fill=tk.X, pady=(2, 10))

        for text, var_name, setter in (
                ("Show atoms and bonds", "show_atoms", self.scene.set_show_atoms),
                ("Show grid box", "show_box", self.scene.set_show_box),
                ("Smooth surfaces", "smooth", self.scene.set_smooth)):
            var = tk.BooleanVar(value=getattr(self.scene, var_name))
            setattr(self, "v_" + var_name, var)
            tk.Checkbutton(
                body, text=text, variable=var,
                command=lambda v=var, f=setter: (f(v.get()), self._refresh()),
                bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_MID,
                activebackground=BG_DARK, activeforeground=TEXT_PRIMARY,
                highlightthickness=0, bd=0, font=("Helvetica", 10),
            ).pack(anchor=tk.W)

        footer = tk.Frame(self, bg=BG_MID, padx=18, pady=10)
        footer.pack(fill=tk.X)
        FlatButton(footer, text="Reset view", command=self._reset,
                   bg=BTN_INVERT, hover="#606878", font_size=9).pack(side=tk.LEFT)
        FlatButton(footer, text="Close", command=self._close,
                   bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10,
                   width=8).pack(side=tk.RIGHT)
        self._update_iso_label()

    def _update_iso_label(self):
        self.iso_lbl.config(text=f"\u00b1 {self.iso.get():.5f}")

    def _on_iso(self, _v=None):
        self._update_iso_label()
        if getattr(self, "_iso_job", None):
            self.after_cancel(self._iso_job)
        # Rebuilding marching cubes on every pixel of slider travel would
        # stutter; one rebuild once the slider settles is enough.
        self._iso_job = self.after(120, self._apply_iso)

    def _apply_iso(self):
        self._iso_job = None
        self.scene.set_isovalue(self.iso.get())
        self._refresh()

    def _on_opacity(self, _v=None):
        self.scene.set_opacity(self.op.get())
        self._refresh()

    def _reset(self):
        self.scene.reset_camera()
        self._refresh()

    def _refresh(self):
        self.app._show_image(keep_zoom=True, recenter=True)

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


class CubeExportDialog(tk.Toplevel):
    """Export the current 3D view as raster or vector, at a chosen scale."""

    def __init__(self, app, scene):
        super().__init__(app.root)
        self.app, self.scene = app, scene
        self._closed = False
        app.suspend_shortcuts()

        self.title("Export 3D View")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(False, False)

        s = app.settings
        self.fmt = tk.StringVar(value=s.get("cube_export_format", "png"))
        self.scale = tk.IntVar(value=s.get("cube_export_scale", 2))
        self.white = tk.BooleanVar(value=s.get("cube_export_white", True))
        self.transparent = tk.BooleanVar(
            value=s.get("cube_export_transparent", False))

        self._build()
        fit_to_screen(self)
        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Export 3D View", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(hdr, text=os.path.basename(self.scene.path), bg=BG_MID,
                 fg=TEXT_MUTED, font=("Helvetica", 9)).pack(anchor=tk.W)

        body = tk.Frame(self, bg=BG_DARK, padx=20, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="FORMAT", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Helvetica", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))

        for key, label, kind in cube_viewer.EXPORT_FORMATS:
            row = tk.Frame(body, bg=BG_DARK)
            row.pack(fill=tk.X, anchor=tk.W)
            tk.Radiobutton(
                row, text=label, value=key, variable=self.fmt,
                command=self._sync, bg=BG_DARK, fg=TEXT_PRIMARY,
                selectcolor=BG_MID, activebackground=BG_DARK,
                activeforeground=TEXT_PRIMARY, highlightthickness=0, bd=0,
                font=("Helvetica", 10), anchor=tk.W,
            ).pack(side=tk.LEFT)
            note = ("resolution-independent" if kind == "vector"
                    else "uses the multiplier below")
            tk.Label(row, text=note, bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Helvetica", 8)).pack(side=tk.LEFT, padx=(8, 0))

        tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=12)

        self.res_head = tk.Label(body, text="RESOLUTION", bg=BG_DARK,
                                 fg=TEXT_MUTED, font=("Helvetica", 9, "bold"))
        self.res_head.pack(anchor=tk.W, pady=(0, 4))

        self.scale_row = tk.Frame(body, bg=BG_DARK)
        self.scale_row.pack(fill=tk.X)
        self._scale_btns = {}
        for mult in cube_viewer.SCALE_CHOICES:
            b = FlatButton(self.scale_row, text=f"{mult}x",
                           command=lambda m=mult: self._set_scale(m),
                           bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=9, width=4)
            b.pack(side=tk.LEFT, padx=3)
            self._scale_btns[mult] = b

        self.dims_lbl = tk.Label(body, text="", bg=BG_DARK, fg=FLAG_TEXT,
                                 font=("Helvetica", 10, "bold"))
        self.dims_lbl.pack(anchor=tk.W, pady=(8, 0))

        self.opt_frame = tk.Frame(body, bg=BG_DARK)
        self.opt_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Checkbutton(self.opt_frame, text="White background (for publication)",
                       variable=self.white, bg=BG_DARK, fg=TEXT_PRIMARY,
                       selectcolor=BG_MID, activebackground=BG_DARK,
                       activeforeground=TEXT_PRIMARY, highlightthickness=0,
                       bd=0, font=("Helvetica", 10),
                       command=self._sync).pack(anchor=tk.W)
        self.trans_cb = tk.Checkbutton(
            self.opt_frame, text="Transparent background (PNG / TIFF only)",
            variable=self.transparent, bg=BG_DARK, fg=TEXT_PRIMARY,
            selectcolor=BG_MID, activebackground=BG_DARK,
            activeforeground=TEXT_PRIMARY, highlightthickness=0, bd=0,
            font=("Helvetica", 10), command=self._sync)
        self.trans_cb.pack(anchor=tk.W)

        footer = tk.Frame(self, bg=BG_MID, padx=20, pady=10)
        footer.pack(fill=tk.X)
        FlatButton(footer, text="Export", command=self._export,
                   bg=BTN_PROCESS, hover=BTN_PROCESS_HOV, font_size=10,
                   width=9).pack(side=tk.RIGHT, padx=(6, 0))
        FlatButton(footer, text="Cancel", command=self._close,
                   bg=BTN_NAV, hover=BTN_NAV_HOV, font_size=10,
                   width=8).pack(side=tk.RIGHT)
        self._set_scale(self.scale.get())

    def _set_scale(self, mult):
        self.scale.set(mult)
        self._sync()

    def _sync(self):
        """Keep the controls consistent with the chosen format."""
        vector = cube_viewer.FORMAT_KIND[self.fmt.get()] == "vector"
        cw, ch = self.app._canvas_size()

        for mult, b in self._scale_btns.items():
            chosen = (mult == self.scale.get()) and not vector
            b.configure(bg=BTN_KEYS if chosen else BTN_NAV,
                        hover=BTN_KEYS_HOV if chosen else BTN_NAV_HOV,
                        state=tk.DISABLED if vector else tk.NORMAL)

        if vector:
            self.res_head.config(fg="#4a4a66")
            self.dims_lbl.config(
                text="Vector output — scales to any size without loss",
                fg=TEXT_MUTED)
        else:
            self.res_head.config(fg=TEXT_MUTED)
            m = self.scale.get()
            mp = (cw * m) * (ch * m) / 1e6
            self.dims_lbl.config(text=f"{cw * m} x {ch * m} px   ({mp:.1f} MP)",
                                 fg=FLAG_TEXT)

        can_trans = (not vector and self.fmt.get() in ("png", "tiff")
                     and not self.white.get())
        self.trans_cb.configure(state=tk.NORMAL if can_trans else tk.DISABLED,
                                fg=TEXT_PRIMARY if can_trans else "#4a4a66")

    def _export(self):
        fmt = self.fmt.get()
        default = os.path.splitext(os.path.basename(self.scene.path))[0]
        path = filedialog.asksaveasfilename(
            title="Export 3D view",
            defaultextension="." + fmt,
            initialdir=os.path.dirname(self.scene.path),
            initialfile=f"{default}.{fmt}",
            filetypes=[(cube_viewer.FORMAT_LABEL[fmt], f"*.{fmt}"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            info = self.scene.export(
                path, fmt=fmt, scale=self.scale.get(),
                transparent=self.transparent.get(),
                white_background=self.white.get())
        except Exception as exc:
            messagebox.showerror("Export failed", f"{type(exc).__name__}: {exc}")
            return

        self.app.settings.update({
            "cube_export_format": fmt,
            "cube_export_scale": self.scale.get(),
            "cube_export_white": self.white.get(),
            "cube_export_transparent": self.transparent.get(),
        })
        save_config(self.app.bindings, self.app.settings)
        size = os.path.getsize(path) / 1024
        messagebox.showinfo("Exported",
                            f"{os.path.basename(path)}\n\n{info}\n"
                            f"{size:.0f} KB")
        self._close()

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


# ─── Exit confirmation ────────────────────────────────────────────────────────
class ExitDialog(tk.Toplevel):
    """
    Quit confirmation, with a warning when notes would be lost from view.

    The notes themselves are always safe on disk in the folder's sidecar file
    — this warns that they have never been written to a shareable .txt, which
    is the thing people actually forget after a long review session.

    result is one of: "quit", "export", "cancel".
    """

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.result = "cancel"

        self.unexported = bool(app.notes) and not app.notes_exported

        app.suspend_shortcuts()
        self.title("Quit " + APP_NAME)
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(False, False)

        self._build()
        fit_to_screen(self)

        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._pick("cancel"))
        self.bind("<Return>", lambda e: self._pick(
            "export" if self.unexported else "quit"))
        self.protocol("WM_DELETE_WINDOW", lambda: self._pick("cancel"))
        self.wait_window()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, padx=22, pady=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"Quit {APP_NAME}?", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 15, "bold")).pack(anchor=tk.W)

        body = tk.Frame(self, bg=BG_DARK, padx=22, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        if self.unexported:
            n = len(self.app.notes)
            with_text = sum(1 for v in self.app.notes.values() if v.strip())
            warn = tk.Frame(body, bg="#3a2a08", padx=14, pady=12)
            warn.pack(fill=tk.X, pady=(0, 14))
            tk.Label(warn,
                     text=f"{GLYPHS['warn']}  You have unexported notes",
                     bg="#3a2a08", fg=FLAG_TEXT,
                     font=("Helvetica", 11, "bold")).pack(anchor=tk.W)
            detail = (f"{n} flagged file(s)"
                      + (f", {with_text} with written notes" if with_text else ""))
            tk.Label(warn, text=detail, bg="#3a2a08", fg=TEXT_PRIMARY,
                     font=("Helvetica", 10)).pack(anchor=tk.W, pady=(4, 0))
            tk.Label(warn,
                     text="They stay saved in this folder and will reload next "
                          "time,\nbut you haven't written them to a .txt report.",
                     bg="#3a2a08", fg=TEXT_MUTED, justify=tk.LEFT,
                     font=("Helvetica", 9)).pack(anchor=tk.W, pady=(6, 0))
        else:
            msg = "Any marks you've made are saved."
            if self.app.notes:
                msg = f"Your {len(self.app.notes)} note(s) have been exported."
            tk.Label(body, text=msg, bg=BG_DARK, fg=TEXT_PRIMARY,
                     font=("Helvetica", 11)).pack(anchor=tk.W, pady=(0, 12))

        marked = sum(1 for v in self.app.image_states.values() if not v)
        if marked:
            tk.Label(body,
                     text=f"{marked} file(s) are marked DELETE but have not been "
                          f"processed yet.\nNothing is deleted until you run Process.",
                     bg=BG_DARK, fg=TEXT_MUTED, justify=tk.LEFT,
                     font=("Helvetica", 9)).pack(anchor=tk.W, pady=(0, 8))

        footer = tk.Frame(self, bg=BG_MID, padx=22, pady=12)
        footer.pack(fill=tk.X)

        FlatButton(footer, text="Cancel", command=lambda: self._pick("cancel"),
                   bg=BTN_NAV, hover=BTN_NAV_HOV,
                   font_size=10, width=8).pack(side=tk.LEFT)

        FlatButton(footer, text="Quit", command=lambda: self._pick("quit"),
                   bg=BTN_DEL, hover=BTN_DEL_HOV,
                   font_size=10, width=8).pack(side=tk.RIGHT, padx=(8, 0))

        if self.unexported:
            FlatButton(footer, text="Export notes, then quit",
                       command=lambda: self._pick("export"),
                       image=icon("edit-document"),
                       bg=BTN_KEEP, hover=BTN_KEEP_HOV,
                       font_size=10).pack(side=tk.RIGHT)

    def _pick(self, what):
        self.result = what
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


# ─── Help ─────────────────────────────────────────────────────────────────────
class HelpDialog(tk.Toplevel):
    """Reference window: supported formats, workflow, and current shortcuts."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self._closed = False

        app.suspend_shortcuts()
        self.title(f"{APP_NAME} Help")
        self.configure(bg=BG_DARK)
        self.transient(app.root)
        self.resizable(True, True)
        self.minsize(620, 420)

        self._build()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.scroller.fit_content(max_height=int(sh * 0.62), max_width=sw - 120)
        self.update_idletasks()
        self.minsize(min(self.winfo_reqwidth(), sw - 60), 420)
        fit_to_screen(self)

        self.grab_set()
        self.focus_force()
        self.bind("<Escape>", lambda e: self._close())
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ── Small layout helpers ─────────────────────────────────────────────────
    def _heading(self, parent, text):
        tk.Label(parent, text=text.upper(), bg=BG_DARK, fg=ACCENT_BLUE,
                 font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(14, 4))

    def _para(self, parent, text, colour=None):
        tk.Label(parent, text=text, bg=BG_DARK, fg=colour or TEXT_PRIMARY,
                 font=("Helvetica", 9), justify=tk.LEFT, anchor=tk.W,
                 wraplength=560).pack(anchor=tk.W, pady=(0, 4))

    def _build(self):
        hdr = tk.Frame(self, bg=BG_MID, padx=20, pady=12)
        hdr.pack(fill=tk.X)
        brand = tk.Frame(hdr, bg=BG_MID)
        brand.pack(anchor=tk.W)
        logo = _photo_from_b64(LOGO_SMALL_PNG_B64)
        if logo is not None:
            lab = tk.Label(brand, image=logo, bg=BG_MID)
            lab.image = logo
            lab.pack(side=tk.LEFT, padx=(0, 9))
        tk.Label(brand, text=f"{APP_NAME} Help", bg=BG_MID, fg=TEXT_PRIMARY,
                 font=("Helvetica", 15, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text="Review images and PDFs, mark them, convert to PDF, "
                           "and clean up.",
                 bg=BG_MID, fg=TEXT_MUTED, font=("Helvetica", 9)).pack(anchor=tk.W)

        footer = tk.Frame(self, bg=BG_MID, padx=20, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        FlatButton(footer, text="Keyboard Shortcuts",
                   command=self._open_shortcuts, image=icon("keyboard"),
                   bg=BTN_KEYS, hover=BTN_KEYS_HOV,
                   font_size=10).pack(side=tk.LEFT)
        FlatButton(footer, text="Close", command=self._close,
                   bg=BTN_NAV, hover=BTN_NAV_HOV,
                   font_size=10, width=8).pack(side=tk.RIGHT)

        self.scroller = ScrollFrame(self, bg=BG_DARK)
        self.scroller.pack(fill=tk.BOTH, expand=True, padx=(20, 6), pady=12)
        b = self.scroller.body

        # ── Supported file types ──
        self._heading(b, "Supported file types")
        grid = tk.Frame(b, bg=BG_DARK)
        grid.pack(anchor=tk.W, fill=tk.X)
        for i, (tid, label, exts) in enumerate(FILE_TYPES):
            r, c = divmod(i, 2)
            cell = tk.Frame(grid, bg=BG_DARK)
            cell.grid(row=r, column=c, sticky=tk.W, padx=(0, 30), pady=2)
            found = self.app.type_counts.get(tid, 0)
            tk.Label(cell, text=f"{label}", bg=BG_DARK,
                     fg=TEXT_PRIMARY if found else TEXT_MUTED,
                     font=("Helvetica", 10, "bold"), width=6, anchor=tk.W
                     ).pack(side=tk.LEFT)
            tk.Label(cell, text="  ".join(sorted(exts)), bg=BG_DARK,
                     fg=TEXT_MUTED, font=("Helvetica", 9)).pack(side=tk.LEFT)
            if found:
                tk.Label(cell, text=f"  ({found} here)", bg=BG_DARK,
                         fg=BTN_KEEP_HOV, font=("Helvetica", 9)).pack(side=tk.LEFT)

        backend = _resolve_pdf_backend()
        if backend == "pypdf":
            self._para(b, "\nPDF preview is in embedded-image mode: page 1's "
                          "image is extracted. Exact for image-based and scanned "
                          "PDFs. Install pypdfium2 to rasterise vector/text PDFs.",
                       FLAG_TEXT)
        elif backend == "none":
            self._para(b, "\nNo PDF preview backend is installed. PDFs show a "
                          "placeholder but can still be marked. "
                          "Install pypdf or pypdfium2.", BTN_DEL_HOV)
        else:
            self._para(b, f"\nPDF preview via {backend} — full page rendering.",
                       TEXT_MUTED)

        # ── Workflow ──
        self._heading(b, "How it works")
        for n, (title, body) in enumerate([
            ("Open a directory",
             "Every subfolder is scanned for supported files. Use FILE TYPES "
             "in the sidebar to show or hide a format; hiding one keeps its marks."),
            ("Mark each file",
             "Keep or Delete. Nothing is created or deleted until you run "
             "Process, so marking is always safe."),
            ("Flag and annotate (optional)",
             "Flag a file for follow-up, or write a note on it. Export Notes "
             "writes a plain-text report grouped by folder."),
            ("Process",
             "Choose the PDF layout — one per file, one per folder, or a "
             "single combined PDF — and control deletion separately for each "
             "file type."),
        ], start=1):
            row = tk.Frame(b, bg=BG_DARK)
            row.pack(anchor=tk.W, fill=tk.X, pady=3)
            tk.Label(row, text=f"{n}", bg=ACCENT_BLUE, fg="white",
                     font=("Helvetica", 9, "bold"), width=3
                     ).pack(side=tk.LEFT, anchor=tk.N)
            txt = tk.Frame(row, bg=BG_DARK)
            txt.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
            tk.Label(txt, text=title, bg=BG_DARK, fg=TEXT_PRIMARY,
                     font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
            tk.Label(txt, text=body, bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Helvetica", 9), justify=tk.LEFT,
                     wraplength=520).pack(anchor=tk.W)

        # ── Viewing ──
        self._heading(b, "Viewing")
        self._para(b,
                   "Scroll to zoom, drag to pan, double-click toggles fit and "
                   "1:1. Rotate and flip are per file and are applied to the "
                   "exported PDF. Fullscreen hides every panel; press Esc to "
                   "return.")
        self._para(b,
                   "Navigation mode switches between running continuously "
                   "through all folders and wrapping inside the current one. "
                   "Preload mode decodes a whole folder up front — worth "
                   "enabling for folders of PDFs.")

        # ── Where things are saved ──
        self._heading(b, "Where your work is saved")
        self._para(b,
                   f"Notes and orientations live in {VisManager.NOTES_FILENAME} "
                   "inside the folder you opened, so they travel with the "
                   "files. Keep/Delete marks last for the session only — run "
                   "Process to act on them.")
        self._para(b,
                   f"Shortcuts and preferences are stored in "
                   f"{os.path.basename(CONFIG_PATH)} in your home folder.")

        # ── Current shortcuts ──
        self._heading(b, "Current shortcuts")
        kg = tk.Frame(b, bg=BG_DARK)
        kg.pack(anchor=tk.W, fill=tk.X)
        per = (len(ACTIONS) + 1) // 2
        for i, (aid, label, _d, _h) in enumerate(ACTIONS):
            r, c = (i, 0) if i < per else (i - per, 1)
            cell = tk.Frame(kg, bg=BG_DARK)
            cell.grid(row=r, column=c, sticky=tk.W, padx=(0, 26), pady=1)
            tk.Label(cell, text=label, bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Helvetica", 9), width=19, anchor=tk.W
                     ).pack(side=tk.LEFT)
            tk.Label(cell, text=display_binding(self.app.bindings.get(aid)),
                     bg=BG_MID, fg=TEXT_PRIMARY, font=("Helvetica", 9, "bold"),
                     padx=7, pady=1).pack(side=tk.LEFT)

        self.scroller.bind_wheel_recursive()

    def _open_shortcuts(self):
        self._close()
        self.app.open_shortcuts_dialog()

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.app.resume_shortcuts()
        self.destroy()


# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()

    # High-DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Dark defaults for anything Tk paints on its own. During a live resize
    # the OS fills newly exposed area before Tk repaints it, using the
    # window's background — on a light default palette that is the white
    # flash at the trailing edge of the window. Setting the palette before
    # any widget exists makes that fill dark instead.
    try:
        root.tk_setPalette(
            background=BG_DARK, foreground=TEXT_PRIMARY,
            activeBackground=BG_MID, activeForeground=TEXT_PRIMARY,
            selectBackground=ACCENT_BLUE, selectForeground="white",
            highlightBackground=BG_DARK, highlightColor=BORDER,
            insertBackground=TEXT_PRIMARY, troughColor=BG_MID,
        )
    except tk.TclError:
        pass
    root.configure(bg=BG_DARK)

    # ttk keeps its own theme colours, which default to light grey and would
    # otherwise flash the same way.
    try:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY,
                        fieldbackground=BG_MID, bordercolor=BORDER,
                        darkcolor=BG_MID, lightcolor=BG_MID,
                        troughcolor=BG_MID, focuscolor=ACCENT_BLUE)
        style.configure("TProgressbar", background=ACCENT_BLUE,
                        troughcolor=BG_MID, bordercolor=BORDER,
                        lightcolor=ACCENT_BLUE, darkcolor=ACCENT_BLUE)
    except tk.TclError:
        pass

    # Dark title-bar on macOS (best effort)
    try:
        root.tk.call("::tk::unsupported::MacWindowStyle", "style", root._w, "document", "closeBox")
    except Exception:
        pass

    # Window / taskbar icon from the embedded logo
    try:
        icon = _photo_from_b64(LOGO_PNG_B64)
        if icon is not None:
            root.iconphoto(True, icon)
            root._icon_ref = icon        # keep a reference alive
    except Exception:
        pass

    # Windows taskbar grouping: without an explicit AppUserModelID the exe
    # inherits Python's icon in the taskbar even when the window icon is set.
    try:
        if sys.platform == "win32":
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"Anthropic.{APP_NAME}.Reviewer.1")
    except Exception:
        pass

    # Confirm the symbol font actually renders before the UI is built
    probe_glyphs(root)

    app = VisManager(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    try:
        root.mainloop()
    finally:
        # PIL._imagingtk's finalisers run during interpreter shutdown and can
        # touch an already-torn-down Tcl interpreter, producing an intermittent
        # segfault AFTER all application work has completed — harmless in
        # effect but it shows up as a crash dialog on Windows. Every setting is
        # written to disk the moment it changes (see save_config calls), so
        # there is nothing left to flush here; leaving immediately skips the
        # fragile teardown entirely.
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(0)


if __name__ == "__main__":
    main()
