import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.backends.backend_tkagg as tkagg
import tkinter as tk
import statistics
from PIL import Image, ImageTk
import random


def neighbors(coorinates1, coordinates2, radius):
    x, y = coorinates1
    l = []
    for i in range(-radius, radius + 1):
        for j in range(-radius, radius + 1):
            t = [x+i, y+j]
            l.append(t)
    if coordinates2 in l:
        return True
    else:
        return False


# vid = random.randint(1, 2)
vid = 1
cap = cv.VideoCapture(f"rekaw/video_prep/v{vid}.mp4")

dir_dict = { 1: {'s': "l", 'o': '3'},
             2: {'s': "p", 'o': '3'},
             3: {'s': "p", 'o': '5'},}

root = tk.Tk()
root.title("OpenCV + Tkinter GUI")


video_frame = tk.Frame(root)
video_frame.pack()

frame_label = tk.Label(video_frame)
frame_label.pack(side=tk.LEFT)

blend_label = tk.Label(video_frame)
blend_label.pack(side=tk.RIGHT)

knots_label = tk.Label(root, text="Aktualna liczba węzłów: ", font=("Arial", 18))
knots_label.pack()

# Utworzenie ramki dla wykresu
plot_frame = tk.Frame(root)
plot_frame.pack()

# Inicjalizacja wykresu Matplotlib
fig, ax = plt.subplots()
line, = ax.plot([], [])
ax.set_xlabel('t (s)')
ax.set_ylabel('Liczba węzłów')
ax.set_title('Wykres siły wiatru')

canvas = tkagg.FigureCanvasTkAgg(fig, master=plot_frame)
canvas.draw()
canvas.get_tk_widget().pack()


knots_hist = []
knots_this_sec = []

def update():
    global knots_hist
    # Setting up variables
    knots = 3
    right_to_next = True

    # Preparing the image
    isTrue, frame = cap.read()
    blurred = cv.medianBlur(frame, 9)
    blurred2 = cv.bilateralFilter(blurred, 9, 81, 81)
    hsv = cv.cvtColor(blurred2, cv.COLOR_BGR2HSV)
    lower_red = np.array([0, 115,115])
    upper_red = np.array([210, 235, 235])
    bin = np.zeros_like(frame)
    bin_post = cv.inRange(hsv, lower_red, upper_red)
    # Gathering edgepoints
    edgepoints = np.zeros_like(frame)
    edgepoints2 = np.zeros_like(frame)
    main_line = np.zeros_like(frame)

    # Creating outline
    for i in range(len(bin)):
        if dir_dict[vid]['s'] == 'l':
            for j in range(len(bin[i])):
                if bin_post[i][j] == 255:
                    edgepoints[i][j] = [255, 0, 0]
                    break
        else:
            for j in range(len(bin[i])):
                if bin_post[i][len(bin[i]) - j - 1] == 255:
                    edgepoints[i][len(bin[i]) - j - 1] = [255, 0, 0]
                    break

    for j in range(len(bin)):
        for i in range(len(bin[i])):
            if bin_post[i][j] == 255:
                edgepoints2[i][j] = [255, 0, 0]
                break

    outlines = cv.bitwise_and(edgepoints, edgepoints2)

    # Creating list of edges
    edges = []
    edge = []

    for i in range(len(bin)):
        for j in range(len(bin)):
            if edgepoints[i][j][0] == 255 and edgepoints2[i][j][0] == 255:
                if len(edge) == 0:
                    edge.append((i, j))
                elif neighbors(edge[len(edge) - 1], [i, j], 8):
                    edge.append((i, j))
                else:
                    edges.append(edge)
                    edge = [(i, j)]
    edges.append(edge)

    # Clearing disruptions
    for edge in edges.copy():
        if len(edge) < 2:
            edges.remove(edge)
    outlines_cleared = np.zeros_like(frame)
    for edge in edges:
        for cords in edge:
            outlines_cleared[cords[0]][cords[1]] = [255, 0, 0]

    # Drawing outlines
    for i in range(len(edges)):
        edge = edges[i]
        outlines_cleared[edge[0][0]][edge[0][1]] = [0, 255, 0]
        outlines_cleared[edge[len(edge) - 1][0]][edge[len(edge) - 1][1]] = [0, 255, 0]

    # Creating main line that will help us determine the wind strenght
    x = []
    y = []

    for cord in edges[0]:
        x.append(cord[0])
        y.append(cord[1])

    coef = np.polyfit(x[0: len(x) - 1], y[0:len(y) - 1], 1)

    a, b = coef

    main_line_cords = []

    # Drawing main line
    for i in range(len(main_line)):
        y_cord = round((a * i) + b)
        if 0 <= y_cord < len(main_line[0]):
            main_line[i][y_cord] = [0, 255, 0]
            main_line_cords.append([i, y_cord])

    # Checking whether the cords are above the line
    past_cords = []
    for i in range(1, len(edges)):
        edge = edges[i]
        for cord in edge:
            try:
                if dir_dict[vid]['s'] == 'l':
                    if main_line_cords[cord[0]][1] + 2 >= cord[1]:
                        outlines_cleared[cord[0]][cord[1]] = [0, 0, 255]
                        past_cords.append(cord)
                else:
                    if main_line_cords[cord[0]][1] - 2 <= cord[1]:
                        outlines_cleared[cord[0]][cord[1]] = [0, 0, 255]
                        past_cords.append(cord)
            except IndexError:
                pass

    # Measuring wind strenght according to how many red stripes are above main line
    if len(edges) == int(dir_dict[vid]['o']):
        for i in range(1, len(edges)):
            if right_to_next:
                edge = edges[i]
                j = 0
                for cord in edge:
                    if cord in past_cords:
                        j += 1
                if j == len(edge):
                    knots += 6
                    right_to_next = True
                elif j > 0:
                    knots += 3
                    right_to_next = False
                else:
                    right_to_next = False
            else:
                break
        # else:
        #     print("Unable to measure due to vid quality")
    knots_this_sec.append(knots)
    # print(f"Knots: {knots}")

    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    frame_alt = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    GRAY = cv.resize(gray, (512, 512))
    GRAY_color = cv.cvtColor(GRAY, cv.COLOR_GRAY2BGR)
    full = cv.bitwise_or(outlines_cleared, main_line)
    FRAME = cv.resize(frame_alt, (512, 512))
    FULL = cv.resize(full, (512, 512))
    BLEND = cv.addWeighted(FULL, 0.5, GRAY_color, 0.5, 0)


    knots_label.config(text=f"Aktualna liczba węzłów: {knots}")

    pil_frame = Image.fromarray(FRAME)
    pil_blend = Image.fromarray(BLEND)
    frame_tk = ImageTk.PhotoImage(image=pil_frame)
    blend_tk = ImageTk.PhotoImage(image=pil_blend)

    frame_label.imgtk = frame_tk
    frame_label.configure(image=frame_tk)
    blend_label.imgtk = blend_tk
    blend_label.configure(image=blend_tk)

    if len(knots_this_sec) == 20:
        knots_hist.append(statistics.fmean(knots_this_sec))
        knots_this_sec.clear()
        ax.plot(range(len(knots_hist)), knots_hist, color='red')
    canvas.draw()

    if isTrue:
        root.after(20, update)
    else:
        cap.release()
        cv.destroyAllWindows()


update()


root.mainloop()
