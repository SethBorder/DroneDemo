import tkinter as tk
import random
import sys
import time
import cProfile

from collections import OrderedDict

from drone import Drone

# Turn on for extra information. (See corresponding setting in drone.py as well.)
DEBUG = False

# Turn off to stop showing the IDs on each drone. (Useful for very large boards.)
SHOW_IDS = True

# Turn on to destroy DYN_NUM drones every DYN_TIME cycles. The drones will be
# replaced one per cycle starting a cycle after they are destroyed.
# If ONE_SPAWN is True, all new drones start at (1, 1). Otherwise they start at
# random locations on the board.
DYNAMIC_MODE = False
DYN_TIME = 10
DYN_NUM = 5
ONE_SPAWN = False

# When set to True, will override NUM_DRONES and create exactly as many drones
# as there are target squares on the board. (Mostly...)
EXACT_COVERAGE = True

class Driver(tk.Canvas):

    NUM_DRONES = 2
    TURN_TIME = 100
    X_DIM = 10
    Y_DIM = 10

    HEIGHT = 600
    WIDTH = 600

    graphics = {}
    obstacle_graphics = {}
    drones = OrderedDict()
    board = {(5, 0): "X", (0, 5): "X", (5, 5): "X"}

    pattern_graphics = []
    points = []
    target_cells = []
    cell_graphics = []

    drones_made = 0
    time = 0
    processing_time = 0

    def __init__(self, root):
        tk.Canvas.__init__(self, root, bg='#FFFFFF', bd=0, height=self.HEIGHT, width=self.WIDTH, highlightthickness=0)
        self.pack()
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Key>", self.enter)
        self.focus_set()
        self.display_message()
        # self.start()

    def display_message(self):
        self.pattern_graphics.append(
            self.create_text(
                self.WIDTH/2,
                self.HEIGHT/2,
                text="Draw a pattern for the bots! (Then hit enter.)"))

    def drag(self, event):
        x = event.x
        y = event.y
        self.points.append((x, y))
        point = self.create_oval(x-1, y-1, x+1, y+1, width=1, fill="black")
        self.pattern_graphics.append(point)

    def debug_click(self, event):
        x = event.x
        y = event.y
        print("Click at ({}, {})".format(x, y))
        cell = (int(self.X_DIM * x / self.WIDTH),
                int(self.Y_DIM * y / self.HEIGHT))
        if cell not in self.board:
            print("At {} there is nothing!".format(cell))
            return
        at_loc = self.board[cell]
        if at_loc == "X":
            print("At {} is: {}".format(cell, at_loc))
        else:
            drone = self.drones[str(at_loc)]
            drone.drone.debug_dump()

    def enter(self, event):
        print("Starting bots!")
        for i in self.pattern_graphics:
            self.delete(i)
        self.unbind("<B1-Motion>")
        self.unbind("<Key>")
        self.bind("<Button-1>", self.debug_click)
        self.start()

    def start(self):
        self.draw_lines()

        self.build_drones()

        self.create_graphics()

        print("Visualizations created. Starting simulation.")
        self.after(self.TURN_TIME, self.update)

    def draw_lines(self):
        print("Drawing board.")
        for i in range(1, self.X_DIM):
            x_loc = i * self.WIDTH / self.X_DIM
            self.create_line(
                x_loc,
                0,
                x_loc,
                self.HEIGHT)
        for i in range(1, self.Y_DIM):
            y_loc = i * self.HEIGHT / self.Y_DIM
            self.create_line(
                0,
                y_loc,
                self.WIDTH,
                y_loc)
        cell_graphics = []
        # Append with two "buffer" cells for each wall, for the border.
        self.target_cells.append((self.X_DIM + 4, self.Y_DIM + 4))
        for p in self.points:
            box_width = (self.WIDTH / self.X_DIM)
            box_height = (self.HEIGHT / self.Y_DIM)
            x_box = p[0] // box_width
            y_box = p[1] // box_height
            if x_box < 0 or x_box >= self.X_DIM or y_box < 0 or y_box >= self.Y_DIM:
                continue
            x_center = (x_box) * box_width + 0.5 * box_width
            y_center = (y_box) * box_height + 0.5 * box_height
            # Add two to account for the border.
            if (int(x_box + 2), int(y_box + 2)) not in self.target_cells:
                self.target_cells.append((int(x_box + 2), int(y_box + 2)))
                self.cell_graphics.append(
                    self.create_rectangle(
                        x_center - 0.5 * box_width,
                        y_center - 0.5 * box_height,
                        x_center + 0.5 * box_width,
                        y_center + 0.5 * box_height,
                        fill="#AAAAAA"))
        if EXACT_COVERAGE:
            # Reassign the "constant" if we're in EXACT_COVERAGE mode.
            # Dirty pool, I know, but other than this it's read-only.
            self.NUM_DRONES = len(self.target_cells) - 1

    def build_drones(self):
        print("Building drones.")
        for i in range(self.NUM_DRONES):
            self.make_drone()

    def make_drone(self, x=None, y=None):
        tries = 0
        while (tries == 0 or (tries < 10 and
              (self.drone_collision(drone) or self.obstacle_crash(drone)))):
            tries += 1
            drone = AbsDrone(
                Drone(
                    self.drones_made,
                    self.target_cells,
                    self.NUM_DRONES),
                x if x else random.randint(0, self.X_DIM-1),
                y if y else random.randint(0, self.Y_DIM-1))
            if x and y:
                x += 1 if random.randint(0, 1) else -1
                y += 1 if random.randint(0, 1) else -1
        if tries == 10:
            print("Unable to create drone {}!".format(self.drones_made))

        self.board[(drone.x, drone.y)] = str(drone.drone.num)
        self.drones[str(self.drones_made)] = drone
        self.drones_made += 1
        return drone

    def create_graphics(self):
        print("Drones built. Creating visualizations.")

        for obstacle in self.board:
            if self.board[obstacle] == "X":
                self.obstacle_graphics[obstacle] = self.create_oval(
                    *self.get_rect_and_mid(*obstacle)[0], fill="#4444ff")

        for drone in self.drones.values():
            self.draw_drone_graphic(drone)

    def draw_drone_graphic(self, drone, new=False):
        drone_draw_pos = self.get_drone_draw_pos(drone)
        d_rect = self.create_rectangle(
            *drone_draw_pos[0],
            fill = 'red' if not new else 'magenta')
        d_text = self.create_text(
            *drone_draw_pos[1],
            text=str(drone.drone.num),
            font=('arial', 28))
        self.graphics[drone] = (d_rect, d_text)

    def update(self):
        # Time the method, so we can subtract our time processing from how long
        # each step should take. It helps a little. Also profile it.
        if DEBUG:
            start = time.time()
            pr = cProfile.Profile()
            pr.enable()

            print("Drones size: {}".format(sys.getsizeof(self.drones)))
            print("Graphics size: {}".format(sys.getsizeof(self.graphics)))
            print("Obstacle Graphics size: {}".format(sys.getsizeof(self.obstacle_graphics)))
            print("Board size: {}".format(sys.getsizeof(self.board)))

        self.time += 1

        new_board = self.board.copy()
        # Clear all drones from board, to avoid problems.
        for k in list(new_board):
            if new_board[k] != "X":
                del new_board[k]


        if DYNAMIC_MODE:
            self.make_and_destroy()

        # Use list() to allow modification during iteration, in case of crash.
        for drone_num in list(self.drones.keys()):
            drone = self.drones[drone_num]
            _map = self.make_map(drone)

            move = drone.drone.update(_map, self.send_message)

            drone.x += move[0]
            drone.y += move[1]
            if self.obstacle_crash(drone):
                self.destroy_drone(drone)
            else:
                # Note later drones can overwrite earlier ones here. This is
                # semi-intentional, and the collision method ensures that all
                # drones except the one with current claim to the tile will
                # crash, which seems reasonable. Just imagine they have
                # battering rams on the front, so whoever gets there second
                # crushes the first guy.
                new_board[(drone.x, drone.y)] = str(drone.drone.num)
        self.board = new_board
        for drone in list(self.drones.values()):
            if self.drone_collision(drone):
                self.destroy_drone(drone)
        if DEBUG:
            stop = time.time()
            self.processing_time = stop - start
            print("Processing drones took {}s.".format(stop - start))
            pr.disable()
            pr.print_stats(sort='time')
        self.draw()

    def make_and_destroy(self):
        if len(self.drones) < self.NUM_DRONES:
            if ONE_SPAWN:
                drone = self.make_drone(1, 1)
            else:
                drone = self.make_drone()

            self.draw_drone_graphic(drone, new=True)
        if self.time % DYN_TIME == 0 and self.drones:
            for i in range(min(DYN_NUM, len(self.drones))):
                drone = random.choice(self.drones.values())
                self.destroy_drone(drone)

    def send_message(self, to):
        return self.get_drone(to).msg

    def make_map(self, drone):
        map = {}
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1),
            (1, -1), (-1, -1), (0, 2), (0, -2), (2, 0), (-2, 0)]
        for d in directions:
            char = 'O'
            new_x = drone.x + d[0]
            new_y = drone.y + d[1]
            if (new_x >= self.X_DIM or new_y >= self.Y_DIM
            or new_x < 0 or new_y < 0):
                char = 'X'
            if (new_x, new_y) in self.board:
                char = self.board[(new_x, new_y)]
            map[d] = char
        return map

    def get_drone(self, n):
        if not n in self.drones:
            self.debug_dump()
            raise RuntimeError("Could not find drone #{}".format(n))
        else:
            return self.drones[n].drone

    def draw(self):
        for drone in self.graphics:
            drone_draw_pos = self.get_drone_draw_pos(drone)
            self.coords(self.graphics[drone][0], *drone_draw_pos[0])
            # Turn red after being magneta for their first cycle on the board.
            if drone.drone.t == 2:
                self.itemconfig(self.graphics[drone][0], fill="red")
            self.coords(self.graphics[drone][1], *drone_draw_pos[1])
        self.after(max(0, int(self.TURN_TIME - self.processing_time)), self.update)

    def get_drone_draw_pos(self, drone):
        return self.get_rect_and_mid(drone.x, drone.y)

    def get_rect_and_mid(self, x, y):
        rect_width = self.WIDTH / self.X_DIM
        rect_height = self.HEIGHT / self.Y_DIM
        drone_x_mid = (x + 0.5) * rect_width
        drone_y_mid = (y + 0.5) * rect_height

        d_rect = (
            drone_x_mid - 0.4 * rect_width,
            drone_y_mid - 0.4 * rect_height,
            drone_x_mid + 0.4 * rect_width,
            drone_y_mid + 0.4 * rect_height,
            )
        d_text = (
            drone_x_mid,
            drone_y_mid,
            )
        return (d_rect, d_text)

    def obstacle_crash(self, drone):
        # Check for collisions
        drone_loc = (drone.x, drone.y)
        if drone_loc in self.board:
            object_present = self.board[drone_loc]
            if object_present == "X":
                print("Drone {} crashed into an obstacle at {}!"
                    .format(drone.drone.num, drone_loc))
                return True

        # Check for out-of-bounds
        if (drone.x < 0 or drone.y < 0
            or drone.x >= self.X_DIM or drone.y >= self.Y_DIM):
            print("Drone {} went out of bounds at {} and crashed!"
                .format(drone.drone.num, drone_loc))
            return True

        return False

    def drone_collision(self, drone):
        # Check for collisions
        for d in self.drones.values():
            if ((drone.x, drone.y) == (d.x, d.y)
                and drone.drone.num != d.drone.num):
                # All drones except the last one to move into a tile crash.
                if self.board[(drone.x, drone.y)] != str(drone.drone.num):
                    print("Drone {} crashed into drone {}!"
                        .format(drone.drone.num, d.drone.num))
                    print("Absolute position: {}".format((drone.x, drone.y)))
                    drone.drone.print_map()
                    print("It had choreographs of {}"
                        .format(drone.drone.choreographed_moves))

                    return True

        return False

    def destroy_drone(self, drone):
        if DEBUG: print("Destroying drone {}!".format(drone.drone.num))
        for i in self.graphics[drone]:
            self.delete(i)
        del self.graphics[drone]
        del self.drones[str(drone.drone.num)]
        drone_loc = (drone.x, drone.y)
        if (drone_loc in self.board
          and self.board[drone_loc] == str(drone.drone.num)):
            del self.board[drone_loc]

    def debug_dump(self, **kwargs):
        print("Board: {}\n".format(self.board))
        print("Drones: {}\n".format(self.drones))
        print("Drone Graphics: {}\n".format(
            ["{}: {}".format(str(d), v) for d, v in self.graphics.items()]))
        print("Obstacle Graphics: {}\n".format(self.obstacle_graphics))
        for k,v in kwargs.items():
            print("{}: {}\n".format(k, v))

class AbsDrone():
    def __init__(self, drone, x, y):
        self.drone = drone
        self.x = x
        self.y = y

    def __str__(self):
        return "#{}: ({}, {})".format(self.drone.num, self.x, self.y)

    def __repr__(self):
        return self.__str__()
