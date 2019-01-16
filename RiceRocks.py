# http://www.codeskulptor.org/#user16_vAlUKonVt7G6IT9_9.py
#
# RiceRocks program
# By Martin Heinsdorf for Rice MOOC on Interactive Python.
# Extra deluxe features: 
#   - Last Score is displayed when game ends.
#   - Asteroids velocity distribution favors fast asteroids.
#   - Animated sprites and explosions have been implemented.

import simplegui
from math import sqrt, cos, sin, floor
from random import random

# globals for user interface
WIDTH = 800
HEIGHT = 600
SCREEN = (WIDTH, HEIGHT)
MAX_ROCKS = 12

# dynamic globals
score = 0
lives = 3
time = 0
last_score = 0
explosion_group = set()

# physical constants
FRICTION_COEF = 0.014 # scalar
THRUST_COEF = 0.1     # pixels/second^2
ANGULAR_ACC = 0.04    # radians/second^2
MUZZLE_VEL = 7        # pixels/second

class Started:
    def __init__(self):
        self.started = False
        
    def get(self):
        return self.started
        
    def set(self, starting):
        self.started = starting
        if starting:
            soundtrack.play()
        else:
            soundtrack.rewind()
            
started = Started()

class ImageInfo:
    def __init__(self, center, size, radius = 0, lifespan = None, animated = False):
        self.center = center
        self.size = size
        self.radius = radius
        if lifespan:
            # lifespan := the number of 1/60 sec frames := the number of animation cells
            self.lifespan = lifespan
        else:
            self.lifespan = float('inf')
        self.animated = animated

    def get_center(self):
        return self.center

    def get_size(self):
        return self.size

    def get_radius(self):
        return self.radius

    def get_lifespan(self):
        return self.lifespan

    def get_animated(self):
        return self.animated
 
# art assets created by Kim Lathrop, may be freely re-used in non-commercial projects, please credit Kim
    
# debris images - debris1_brown.png, debris2_brown.png, debris3_brown.png, debris4_brown.png
#                 debris1_blue.png, debris2_blue.png, debris3_blue.png, debris4_blue.png, debris_blend.png
debris_info = ImageInfo([320, 240], [640, 480])
debris_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/debris2_blue.png")

# nebula images - nebula_brown.png, nebula_blue.png
nebula_info = ImageInfo([400, 300], [800, 600])
nebula_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/nebula_blue.png")

# splash image
splash_info = ImageInfo([200, 150], [400, 300])
splash_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/splash.png")

# ship image
ship_info = ImageInfo([45, 45], [90, 90], 35)
ship_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/double_ship.png")

# missile image - shot1.png, shot2.png, shot3.png
missile_info = ImageInfo([5,5], [10, 10], 3, 50)
missile_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/shot2.png")

# asteroid images - asteroid_blue.png, asteroid_brown.png, asteroid_blend.png
asteroid_info = ImageInfo([45, 45], [90, 90], 40)
asteroid_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/asteroid_blue.png")

# animated explosion - explosion_orange.png, explosion_blue.png, explosion_blue2.png, explosion_alpha.png
explosion_info = ImageInfo([64, 64], [128, 128], 17, 24, True)
explosion_image = simplegui.load_image("http://commondatastorage.googleapis.com/codeskulptor-assets/lathrop/explosion_alpha.png")

# sound assets purchased from sounddogs.com, please do not redistribute
soundtrack = simplegui.load_sound("http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/soundtrack.mp3")
missile_sound = simplegui.load_sound("http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/missile.mp3")
missile_sound.set_volume(.5)
ship_thrust_sound = simplegui.load_sound("http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/thrust.mp3")
explosion_sound = simplegui.load_sound("http://commondatastorage.googleapis.com/codeskulptor-assets/sounddogs/explosion.mp3")

# helper functions
def angle_to_vector(ang):
    return [cos(ang), sin(ang)]

def dist(p, q):
    """ distance (pixels) between two toroidally adjusted positions """
    return sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)

def process_sprite_group(sprite_group, canvas):
    for sprite in set(sprite_group):
        if sprite.update():
            sprite_group.remove(sprite)
        sprite.draw(canvas)
        
def group_collide(group, other_object):
    """ 
        Count the collisions between members of the group
        and the other_object. Delete the colliding members.
    """
    count = 0
    for sprite in set(group.get_group()):
        if sprite.collide(other_object):
            explosion_group.add(Sprite(other_object.pos, [0,0], \
                                 0, 0, explosion_image, explosion_info, explosion_sound))
            group.remove(sprite)
            count += 1
    return count 

def group_group_collide(group, other_group):
    """ 
        Count the collisions between members of the group and any
        members of the other_group. Delete both colliding members.
    """
    count = 0
    for sprite in set(group.get_group()):
        if group_collide(other_group, sprite):
             group.remove(sprite)
             count += 1
    return count

def vran():
    """ 
        Return a random number with a V-shaped distribution in the range(-1, 1)
        with mean 0, biased away from 0 to avoid generating too many slow objects.
    """
    z = random()                 # For this symmetric distributions, it's easiest
    sign = 2 * floor(2 * z) - 1  # to use the inverse CDF to generate one side
    return sign * sqrt(z)        # and apply a random sign afterwards.
    
# Sprite class
class Sprite:
    def __init__(self, pos, vel, ang, ang_vel, image, info, sound = None):
        self.pos = [pos[0],pos[1]]
        self.vel = [vel[0],vel[1]]
        self.angle = ang
        self.angle_vel = ang_vel
        self.image = image
        self.image_center = info.get_center()
        self.image_size = info.get_size()
        self.radius = info.get_radius()
        self.lifespan = info.get_lifespan()
        self.animated = info.get_animated()
        self.age = 0
        if sound:
            sound.rewind()
            sound.play()
   
    def draw(self, canvas):
        if self.animated:
            current_index = (self.age % self.lifespan) // 1
            current_center = [self.image_center[0] +  current_index * self.image_size[0], \
                              self.image_center[1]]
            canvas.draw_image(self.image, current_center, self.image_size, \
                              [self.pos[0] % WIDTH, self.pos[1] % HEIGHT], self.image_size) 
        else:
            canvas.draw_image(self.image, [self.image_center[0], self.image_center[1]], \
                              self.image_size, [self.pos[0] % WIDTH, self.pos[1] % HEIGHT], \
                              self.image_size, self.angle)
    
    def update(self):
        """ Return True if sprite is has expired, False if not. """
        self.age += 1
        if self.age > self.lifespan:
            return True
        for i in range(2):
            self.pos[i] = (self.pos[i] + self.vel[i]) % SCREEN[i]
        self.angle += self.angle_vel
        return False
        
    def get_radius(self):
        return self.radius
    
    def get_position(self):
        return self.pos
        
    def collide(self, other_object):
        current_distance = dist(self.get_position(), other_object.get_position())
        touching_distance = self.get_radius() + other_object.get_radius()
        return current_distance <= touching_distance          

# Ship class can borrow some Sprite accessor functions.
class Ship (Sprite):
    def __init__(self, pos, vel, angle, image, info):
        self.pos = [pos[0], pos[1]]
        self.vel = [vel[0], vel[1]]
        self.thrust = False
        self.angle = angle
        self.angle_vel = 0
        self.image = image
        self.image_center = info.get_center()
        self.image_size = info.get_size()
        self.radius = info.get_radius()

    def set_thrust(self, thrust):
        self.thrust = thrust
        if thrust:
            ship_thrust_sound.play()
        else:
            ship_thrust_sound.rewind()
        
    def draw(self,canvas):
        canvas.draw_image(self.image, \
                          [self.image_center[0] + int(self.thrust) * 90, self.image_center[1]], \
                          self.image_size, \
                          [self.pos[0] % WIDTH, self.pos[1] % HEIGHT], \
                          self.image_size, self.angle)

    def update(self):
        thrust = [0, 0]
        thrust_direction = angle_to_vector(self.angle)
        acceleration = [0, 0]

        for i in range(2):
            if self.thrust:
                thrust[i] = thrust_direction[i] * THRUST_COEF
            acceleration[i] = thrust[i] - FRICTION_COEF * self.vel[i]
            self.vel[i] += acceleration[i]
            self.pos[i] = (self.pos[i] +self.vel[i]) % SCREEN[i]
        self.angle += self.angle_vel
        
    def change_angular_velocity(self, angular_acc):
        self.angle_vel = angular_acc
        
    def shoot(self):
        forward = angle_to_vector(self.angle)
        missile_group.add(Sprite([self.pos[0] + self.radius * forward[0], \
                                  self.pos[1] + self.radius * forward[1]], \
                                 [self.vel[0] + MUZZLE_VEL * forward[0], \
                                  self.vel[1] + MUZZLE_VEL * forward[1]], \
                                 0, 0, missile_image, missile_info, missile_sound))
   
class Group:                   # was called RockGroup, but it's more genaral than that
    def __init__(self):
        self.group = set()
        
    def add(self, rock):
        self.group.add(rock)
    
    def draw(self, canvas):
        for rock in self.group:
            rock.draw(canvas)
           
    def update(self):
        for rock in self.group:
            rock.update()
            
    def get_count(self):
        return len(self.group)
           
    def get_group(self):
        return self.group
           
    def remove(self, member):
        self.group.remove(member)
           
def draw(canvas):
    global time, lives, score, last_score
    
    # process collisions
    ship_collisions = group_collide(rock_group, my_ship)
    if ship_collisions:
        lives -= 1
        if not lives:
            last_score = score
            reset_game()
            started.set(False)
            
    rock_collisions = group_group_collide(rock_group, missile_group)
    if rock_collisions:
        score += rock_collisions
    
    # animate background
    time += 1
    center = debris_info.get_center()
    size = debris_info.get_size()
    wtime = (time / 8) % center[0]
    canvas.draw_image(nebula_image, nebula_info.get_center(), nebula_info.get_size(), [WIDTH / 2, HEIGHT / 2], [WIDTH, HEIGHT])
    canvas.draw_image(debris_image, [center[0] - wtime, center[1]], [size[0] - 2 * wtime, size[1]], 
                                [WIDTH / 2 + 1.25 * wtime, HEIGHT / 2], [WIDTH - 2.5 * wtime, HEIGHT])
    canvas.draw_image(debris_image, [size[0] - wtime, center[1]], [2 * wtime, size[1]], 
                                [1.25 * wtime, HEIGHT / 2], [2.5 * wtime, HEIGHT])
    # draw ship and sprites
    my_ship.draw(canvas)
    my_ship.update()
    process_sprite_group(rock_group.get_group(), canvas)
    process_sprite_group(missile_group.get_group(), canvas)
    process_sprite_group(explosion_group, canvas)
        
    # left and right justify top text
    text = "%d%d" % (lives, score)   
    canvas.draw_text("Lives: %d%sScore: %d" % (lives, " " * (12 - len(text)), score), \
                     [10, 35], 50, "#BB44BB", "monospace")
    # center Last Score text
    if last_score:
        text = "%d" % (last_score)
        canvas.draw_text("%s(Last Score: %d)" % (" " * (7 - len(text)), last_score), \
                     [10, 75], 50, "#BB44BB", "monospace")
        
    # splash screen
    if not started.get():
        canvas.draw_image(splash_image, splash_info.get_center(), splash_info.get_size(), \
                          [WIDTH / 2, HEIGHT / 2], splash_info.get_size())
            
# timer handler that spawns a rock    
def rock_spawner():
    global rock_group
    if started.get() and rock_group.get_count() < MAX_ROCKS:
        
        # Don't spawn a rock right near the ship.
        pos = my_ship.get_position()
        touching_distance = my_ship.get_radius() + asteroid_info.get_radius()
        while dist(pos, my_ship.get_position()) <= 2 * touching_distance:
            pos = [WIDTH * random(), HEIGHT * random()]
            
        difficulty = 1 + sqrt(score // 20)
        rock_group.add(Sprite(pos, [difficulty * vran(), difficulty * vran()], \
                       vran(), .15 * vran(), asteroid_image, asteroid_info))

def thruster(is_down):
    my_ship.set_thrust(is_down)
    
def rotate_left(is_down):
    my_ship.change_angular_velocity(- is_down * ANGULAR_ACC)
    
def rotate_right(is_down):
    my_ship.change_angular_velocity(+ is_down * ANGULAR_ACC)
    
def shoot(is_down):
    if is_down:
        my_ship.shoot()
    
key_action_map = { "up": thruster, \
                   "left" : rotate_left, \
                   "right" : rotate_right, \
                   "space" : shoot }
key_action = dict()    
for k in key_action_map.keys():
    key_action[simplegui.KEY_MAP[k]] = key_action_map[k]

def keydown_handler(key):
    key_handler(key, 1)
    
def keyup_handler(key):
    key_handler(key, 0)
    
def key_handler(key, is_down):
    if not started.get():
        return
    if key in key_action.keys():   # guards against KeyError on unmapped keys
        key_action[key](is_down)
        
def mouse_handler(position):
    global last_score
    reset_game()
    last_score = 0
    
def reset_game():
    global score, lives, time, my_ship, rock_group
    rock_group = Group()
    my_ship = Ship([WIDTH / 2, HEIGHT / 2], [0, 0], 0, ship_image, ship_info)
    started.set(True)
    score = 0
    lives = 3
    time = 0
    ship_thrust_sound.rewind()
    
# initialize frame
frame = simplegui.create_frame("Asteroids", WIDTH, HEIGHT)

# initialize ship
my_ship = Ship([WIDTH / 2, HEIGHT / 2], [0, 0], 0, ship_image, ship_info)
rock_group = Group()
missile_group = Group()

# register handlers
frame.set_draw_handler(draw)
frame.set_keydown_handler(keydown_handler)
frame.set_keyup_handler(keyup_handler)
frame.set_mouseclick_handler(mouse_handler)

timer = simplegui.create_timer(1000.0, rock_spawner)

# get things rolling
timer.start()
frame.start()

