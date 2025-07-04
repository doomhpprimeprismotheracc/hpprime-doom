#PYTHON Doom
import hpprime
import graphic
import math

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
EPSILON = 1e-6
RAD_CONST = math.pi / 180

ceiling_clip = [0]*SCREEN_WIDTH
floor_clip = [SCREEN_HEIGHT]*SCREEN_WIDTH

class Color:
    """A color. Uses RGB because it's actually humanly readable and someone did in fact write this code themselves."""
    def __init__(self,r,g,b):
        self.R = r
        self.G = g
        self.B = b

class Texture:
    """Texture file"""
    def __init__(self,fileno):
        self.fileno = fileno
    def load_file(self,surface=9):
        #print("G{0} := AFiles('{1}');".format(str(surface),self.fileno))
        hpprime.eval('G{0} := AFiles("{1}");'.format(str(surface),self.fileno))

class TextureTree:
    """Sorta like camera class but for textures."""
    def __init__(self,surface=9):
        self.tree = {}
        self.loaded = "nil"
        self.surface = surface

    def add_texture(self,fileno):
        self.tree[fileno] = Texture(fileno)

    def load_texture(self,fileno,surface):
        self.loaded = fileno
        self.tree[fileno].load_file(surface)
    def load_texture(self,fileno):
        self.loaded = fileno
        self.tree[fileno].load_file(self.surface)

    def find_texcolumn(self,sx,x0,x1,w=128):
        t = (sx - x0) / (x1 - x0)
        return int(t * w) % w
    
    def find_texrow(self,sx,sy,x0,x1,y0up,y0down,y1up,y1down,h=128):
        t = (sx-x0) / (x1-x0)
        y0 = y0up + t * (y1up - y0up)
        y1 = y0down + t * (y1down - y0down)
        v = (sy - y0) / (y1-y0)
        v = min(0,min(1,v))
        return int(v*h) % h
    
    def find_texpix(self,sx,sy,x0,x1,y0up,y0down,y1up,y1down,w=128,h=128):
        return self.find_texcolumn(sx,x0,x1,w), self.find_texrow(sx,sy,x0,x1,y0up,y0down,y1up,y1down,h)
    

    def get_texture_pixel(self,fileno,x,y):
        if self.loaded != fileno:
            self.load_texture(fileno)
        return "GETPIX_P(G9,{0},{1})".format(str(x),str(y))
        # print("E"+col)
       # return graphic.get_pixel(9,x%128,y%128) #col = str(this)
        #if len(col) < 9:
        col += "0"*(9-len(col))
        rr = int(col[0:3])
        gg = int(col[3:6])
        bb = int(col[6:9])
        try:
            return Color(rr,gg,bb)
        except ValueError:
            print("!")
            return Color(0,0,0)



class Camera:
    """Camera settings, pretty much. Contains projection and drawing functions."""
    def __init__(self,FOV=75):
        self.FOV = FOV*RAD_CONST
    
    def project_point(self,player,point,clip=True):
        """Project a point using the player's perspective. Returns [a] the point's x position along the screen and [b] the point's perpendicular distance to the player."""
        dX = point.x - player.x
        dY = point.y - player.y

        rX = (dX * math.cos(player.r)) - (dY * math.sin(player.r))
        rY = (dX * math.sin(player.r)) + (dY * math.cos(player.r))

        #if rY <= EPSILON:
        #    return -9999, rY

        focal_length = (SCREEN_WIDTH / 2) / math.tan(self.FOV / 2)
        try:
            x0 = (rX * focal_length) / rY + (SCREEN_WIDTH/2)
        except ZeroDivisionError:
            x0 = (rX * focal_length) / (rY-(1e-6)) + (SCREEN_WIDTH/2)

        return x0, rY

    def project_wall(self,player,wall,c=0):
        """Project a wall using Camera.project_point. Returns [a,b] the x positions of the wall's start and end, [c,d] the top and bottom y positions of the wall's start, and [e,f] the top and bottom y positions of the wall's end."""

        def inner():
            if y0 == 0:
                y0 -= EPSILON
            if y1 == 0:
                y1 -= EPSILON

            r0 = (SCREEN_HEIGHT/2) + ((1 * SCREEN_HEIGHT) / (2 * y0))
            r1 = (SCREEN_HEIGHT/2) - ((1 * SCREEN_HEIGHT) / (2 * y0))
            r2 = (SCREEN_HEIGHT/2) + ((1 * SCREEN_HEIGHT) / (2 * y1))
            r3 = (SCREEN_HEIGHT/2) - ((1 * SCREEN_HEIGHT) / (2 * y1))

            return r0,r1,r2,r3

        x0,y0 = self.project_point(player,wall.start)
        x1,y1 = self.project_point(player,wall.end)
        
        if y0 <= EPSILON and y1 <= EPSILON: # Both points behind camera
            return -10,0,0,0,0,0,0
        
        elif (y0 <= EPSILON or y1 <= EPSILON) and (c < 20): # One point behind camera, clipping wall is required

            t = ((EPSILON) - y0) / (y1 - y0)
            nX = wall.start.x + t * (wall.end.x - wall.start.x)
            nY = wall.start.y + t * (wall.end.y - wall.start.y)

            if y0 <= EPSILON:
                x0,y0 = self.project_point(player,Linedef(Point(nX, nY), wall.end).start)
                x1,y1 = self.project_point(player,Linedef(Point(nX, nY), wall.end).end)

            elif y1 <= EPSILON:
                x0,y0 = self.project_point(player,Linedef(wall.start, Point(nX, nY)).start)
                x1,y1 = self.project_point(player,Linedef(wall.start, Point(nX, nY)).end)
            
            r0,r1,r2,r3 = inner()
            return x0,x1,r0,r1,r2,r3,y0-y1
            

        else:
            r0,r1,r2,r3 = inner()
            return x0,x1,r0,r1,r2,r3,y0-y1

    def draw_quad(self,x0,y0,x1,y1,x2,y2,x3,y3,color:Color):
        """Draws a quadrilateral. Included so that this code is more easily adaptable to other platforms."""
        hpprime.eval( "FILLPOLY_P(G1,{0}({1},{2}),({3},{4}),({5},{6}),({7},{8}){9},RGB({10},{11},{12}))".format("{",round(x0),round(y0),round(x1),round(y1),round(x2),round(y2),round(x3),round(y3),"}",color.R,color.G,color.B))
    
    def draw_pix(self,x0,y0,color):
        """Sets a pixel at x0,y0 to color Color. Included so that this code is more easily adaptable to other platforms. TBH this shouldn't even be that hard to implement anyways, but you're welcome."""
        if type(color) == type(Color(255,255,255)): 
            hpprime.eval( "PIXON_P(G1,{0},{1},RGB({2},{3},{4}))".format(str(x0),str(y0),str(color.R),str(color.G),str(color.B)))
        else: 

            hpprime.eval( "PIXON_P(G1,{0},{1},{2})".format(str(x0),str(y0),str(color)))
    
    def draw_wall(self,player,wall,color,ttree,fileno):
        """Draws a wall in color Color. ON THE SCREEN. NO WAY!!!!"""
        x0,x1,r0,r1,r2,r3,yd = self.project_wall(player,wall)
        if (x0,x1,r0,r1,r2,r3) == (-10,0,0,0,0,0):
            return -1
        #self.draw_quad(x0,r0,x0,r1,x1,r3,x1,r2,color)
        self.draw_textured_quad(ttree,fileno,x0,x1,r0,r1,r2,r3)

    def draw_textured_quad(self,ttree:TextureTree,fileno,x0,x1,r0,r1,r2,r3):
        inverse = False
        x0 = int(max(0,min(SCREEN_WIDTH,x0)))
        x1 = int(max(0,min(SCREEN_WIDTH,x1)))
        if x0 == x1: return
        if x0 > x1: 
            x0, x1 = x1, x0
            inverse = True
        for i in range(int(x0),int(x1)+1):
            t = (i-x0) / (x1-x0)
            px = (t*128) % 128
            y0 = r0 + t * (r2 - r0)
            y1 = r1 + t * (r3 - r1)
            y0 = int(max(0,min(SCREEN_HEIGHT,y0)))
            y1 = int(max(0,min(SCREEN_HEIGHT,y1)))
            if y1 - y0 == 0:
                continue
            if y0 > y1:
                y0,y1 = y1,y0
            for j in range(int(y0),int(y1)+1):
                v = (j-y0) / (y1-y0)
                if inverse:
                    v = 1-v
                py = int(v*128) % 128
                col = ttree.get_texture_pixel(fileno, px, py )
                self.draw_pix(i,j,col)
                


class Player:
    def __init__(self,x,y,r):
        self.x = x
        self.y = y 
        self.r = r

class Point:
    """2D coordinate with x/y values."""
    def __init__(self,x,y):
        self.x = x
        self.y = y

class Wall:
    """Generic wall object lol"""
    def __init__(self,start,end):
        self.start = start
        self.end = end
        if type(start) == type(()) or type(start) == type([]): self.start = Point(start[0], start[1])
        if type(end) == type(()) or type(end) == type([]): self.end = Point(end[0], end[1])
        self.dx = self.end.x - self.start.x
        self.dy = self.end.y - self.start.y

Linedef = Wall

class BSPNode:
    """BSP tree node obviously"""
    def __init__(self,partition,left=None,right=None,segments=[]):
        self.partition = partition
        self.left = left
        self.right = right
        self.segments = segments

"""
walls = [
    Wall(Point(2, 18), Point(5, 8)),
    Wall(Point(4, 2), Point(12, 5)),
    Wall(Point(15, 5), Point(10, 10)),
    Wall(Point(5, 8), Point(4, 2)),
    Wall(Point(12, 5), Point(15, 5)),
    Wall(Point(10, 10), Point(2, 18)),
    Wall(Point(8, 12), Point(6, 12)),
    Wall(Point(5, 6), Point(7, 6)),
    ]
"""
walls = [
  Wall(Point(-5, -5), Point(-3, -5)),
  Wall(Point(-5, -5), Point(-5, -2)),
  Wall(Point(5, -5), Point(3, -5)),
  Wall(Point(5, -5), Point(5, -2)),
  Wall(Point(5, 5), Point(3, 5)),
  Wall(Point(5, 5), Point(5, 3)),
  Wall(Point(-5, 3), Point(-5, 5)),
  Wall(Point(-5, 5), Point(-3, 5)),
  Wall(Point(5, 3), Point(10, 3)),
  Wall(Point(5, -2), Point(10, -2)),
  Wall(Point(3, 5), Point(3, 8)),
  Wall(Point(-3, 5), Point(-3, 9)),
  Wall(Point(-3, 9), Point(3, 8)),
  Wall(Point(-5, 3), Point(-10, 3)),
  Wall(Point(-10, -1), Point(-5, -2)),
  Wall(Point(-10, 0), Point(-15, 2)),
  Wall(Point(-10, 0), Point(-10, -1)),
  Wall(Point(-10, 3), Point(-12, 6)),
  Wall(Point(-15, 2), Point(-12, 6)),
  Wall(Point(3, -5), Point(3, -10)),
  Wall(Point(3, -10), Point(10, -10)),
  Wall(Point(10, -10), Point(10, -2)),
  Wall(Point(15, 3), Point(15, -5)),
  Wall(Point(-5, -10), Point(0, -9)),
  Wall(Point(0, -9), Point(0, -12)),
  Wall(Point(0, -12), Point(5, -12)),
  Wall(Point(-8, -10), Point(-8, -5)),
  Wall(Point(-5, -12), Point(-8, -5)),
  Wall(Point(-6, -10), Point(-5, -10)),
  Wall(Point(13, -5), Point(13, -10)),
  Wall(Point(15, -6), Point(16, -6)),
  Wall(Point(16, 3), Point(16, -6)),
  Wall(Point(-7, -8), Point(-6, -8)),
  Wall(Point(-6, -8), Point(-3, -9)),
  Wall(Point(-3, -9), Point(-4, -10)),
  Wall(Point(-3, 4), Point(-3, 3)),
  Wall(Point(-3, 3), Point(-2, 3)),
  Wall(Point(-2, 3), Point(-2, 4)),
  Wall(Point(-2, 4), Point(-3, 4)),
  Wall(Point(10, 5), Point(10, 4)),
  Wall(Point(10, 5), Point(15, 5)),
  Wall(Point(10, 4), Point(5, 4)),
  Wall(Point(-8, -5), Point(-10, -5)),
  Wall(Point(-15, -1), Point(-13, -5)),
  Wall(Point(-12, 1), Point(-12, -1)),
  Wall(Point(-12, -1), Point(-10, -1)),
  Wall(Point(-13, -5), Point(-13, -10)),
  Wall(Point(-10, -5), Point(-10, -10)),
  Wall(Point(-10, -10), Point(-5, -12)),
  Wall(Point(-4, -10), Point(-4, -12)),
  Wall(Point(-4, -12), Point(-2, -12)),
  Wall(Point(-2, -12), Point(-2, -9)),
  Wall(Point(-3, -9), Point(0, -9)),
  Wall(Point(-13, -12), Point(-13, -15)),
  Wall(Point(-13, -15), Point(-5, -15)),
  Wall(Point(0, -15), Point(5, -15)),
  Wall(Point(10, -15), Point(15, -15)),
  Wall(Point(-15, -15), Point(-13, -12)),
  Wall(Point(-15, 0), Point(-20, -5)),
  Wall(Point(-15, 0), Point(-15, -1)),
  Wall(Point(-20, -5), Point(-15, -15)),
  Wall(Point(-17, -4), Point(-17, -3)),
  Wall(Point(-17, -3), Point(-16, -3)),
  Wall(Point(-16, -3), Point(-16, -4)),
  Wall(Point(-16, -4), Point(-17, -4)),
  Wall(Point(-17, -7), Point(-17, -8)),
  Wall(Point(-17, -8), Point(-16, -8)),
  Wall(Point(-16, -8), Point(-16, -7)),
  Wall(Point(-16, -7), Point(-17, -7)),
  Wall(Point(-16, -13), Point(-16, -12)),
  Wall(Point(-16, -12), Point(-14, -12)),
  Wall(Point(-14, -12), Point(-14, -13)),
  Wall(Point(-14, -13), Point(-16, -13)),
  Wall(Point(-9, -3), Point(-9, -3)),
  Wall(Point(-9, -3), Point(-9, -2)),
  Wall(Point(-9, -2), Point(-8, -2)),
  Wall(Point(-8, -2), Point(-8, -3)),
  Wall(Point(-8, -3), Point(-9, -3)),
  Wall(Point(-9, -14), Point(-9, -13)),
  Wall(Point(-9, -13), Point(-8, -13)),
  Wall(Point(-8, -13), Point(-8, -14)),
  Wall(Point(-8, -14), Point(-9, -14)),
  Wall(Point(2, 4), Point(2, 2)),
  Wall(Point(2, 3), Point(3, 3)),
  Wall(Point(3, 3), Point(3, 4)),
  Wall(Point(3, 4), Point(2, 4)),
  Wall(Point(2, 2), Point(3, 3)),
  Wall(Point(1, -13), Point(1, -14)),
  Wall(Point(1, -14), Point(2, -14)),
  Wall(Point(2, -14), Point(2, -13)),
  Wall(Point(2, -13), Point(1, -13)),
  Wall(Point(-5, -15), Point(-5, -17)),
  Wall(Point(0, -15), Point(0, -17)),
  Wall(Point(5, -15), Point(5, -16)),
  Wall(Point(10, -15), Point(10, -17)),
  Wall(Point(5, -16), Point(5, -17)),
  Wall(Point(15, -15), Point(15, -17)),
  Wall(Point(-5, -17), Point(15, -17)),
  Wall(Point(13, -10), Point(15, -6)),
  Wall(Point(15, 5), Point(15, 3)),
  Wall(Point(15, 3), Point(16, 3)),
  Wall(Point(15, -10), Point(15, -15)),
  Wall(Point(15, -10), Point(16, -10)),
  Wall(Point(16, -10), Point(16, -6)),
  Wall(Point(13, -5), Point(14, -5)),
  Wall(Point(14, -5), Point(14, -6)),
  Wall(Point(14, -6), Point(13, -6)),
  Wall(Point(12, 4), Point(11, 3)),
  Wall(Point(11, 3), Point(12, 3)),
  Wall(Point(12, 3), Point(12, 4)),
  Wall(Point(7, -11), Point(7, -12)),
  Wall(Point(7, -12), Point(8, -12)),
  Wall(Point(8, -12), Point(8, -11)),
  Wall(Point(8, -11), Point(7, -11)),
  Wall(Point(-1, -3), Point(-1, -4)),
  Wall(Point(-1, -4), Point(0, -4)),
  Wall(Point(0, -4), Point(0, -3)),
  Wall(Point(0, -3), Point(-1, -3)),
  Wall(Point(-15, 2), Point(-15, 0)),
  Wall(Point(5, 0), Point(7, 0)),
  Wall(Point(7, 0), Point(7, -2)),
  Wall(Point(-3, -5), Point(-3, -7)),
  Wall(Point(-5, -7), Point(-3, -7)),
  Wall(Point(-5, -7), Point(-5, -6)),
  Wall(Point(-2, -12), Point(-1, -12)),
  Wall(Point(1, -10), Point(3, -10)),
  Wall(Point(3, -10), Point(3, -11)),
  Wall(Point(3, -11), Point(4, -10)),
  Wall(Point(3, -11), Point(1, -10)),
  Wall(Point(5, 0), Point(5, -1)),
  Wall(Point(-13, -12), Point(-13, -11)),
  Wall(Point(-5, -15), Point(-5, -14)),
  Wall(Point(-5, -12), Point(-5, -13)),
  Wall(Point(5, -12), Point(5, -13)),
  Wall(Point(5, -15), Point(5, -14)),
  Wall(Point(0, -15), Point(0, -14)),
  Wall(Point(0, -12), Point(0, -13)),
  Wall(Point(-3, -5), Point(-2, -5)),
  Wall(Point(3, -5), Point(2, -5)),
  Wall(Point(-1, -5), Point(1, -5)),
  Wall(Point(-5, 0), Point(-5, -2)),
  Wall(Point(-5, 3), Point(-5, 2)),
  Wall(Point(-10, 0), Point(-10, 2)),
  Wall(Point(-8, -1), Point(-8, 1)),
  Wall(Point(-8, 1), Point(-7, 1)),
  Wall(Point(-7, 1), Point(-7, 0)),
  Wall(Point(-8, -1), Point(-7, -1)),
  Wall(Point(-8, -1), Point(-7, 0)),
  Wall(Point(-7, -1), Point(-7, 0)),
  Wall(Point(14, -10), Point(15, -10)),
  Wall(Point(11, -10), Point(13, -10)),
  Wall(Point(10, -15), Point(10, -12)),
  Wall(Point(-5, -15), Point(-3, -15)),
  Wall(Point(-2, -15), Point(0, -15)),
  Wall(Point(5, -15), Point(6, -15)),
  Wall(Point(7, -15), Point(10, -15)),
  Wall(Point(11, 1), Point(11, -1)),
  Wall(Point(11, -1), Point(12, -1)),
  Wall(Point(12, -1), Point(12, 1)),
  Wall(Point(12, 1), Point(11, 1)),
]

plr = Player(0,0,0)
cam = Camera()

def getdiv_linedef(case,partition):
    try:
        start = getdiv_point(case.start,partition.start,partition.dx,partition.dy) 
        end = getdiv_point(case.end,partition.end,partition.dx,partition.dy) 
    except Exception:
        start = getdiv_point(case.start,partition.start,partition.end.x-partition.start.x,partition.end.y-partition.start.y)
        end = getdiv_point(case.end,partition.end,partition.end.x-partition.start.x,partition.end.y-partition.start.y)
    if start > 0 and end > 0:
        return "back"
    elif start < 0 and end < 0:
        return "front"
    elif start == 0 and end == 0:
        return "on"
    elif start == 0:
        return "back" if end > 0 else "front"
    elif end == 0:
        return "front" if start > 0 else "back"
    else:
        return "span"

def getdiv_point(case,partition,dx,dy):

    # return table:
    # div<0 = behind
    #  div=0 = spanning
    #  div>0 = in front
    return ((case.x - partition.x) * dy) - ((case.y - partition.y) * dx)

def splitdiv_linedef(case,partition):

    dx = [case.start.x - case.end.x, partition.start.x - partition.end.x]
    dy = [case.start.y - case.end.y, partition.start.y - partition.end.y]
    def det(a,b): return a[0] * b[1] - a[1] * b[0]
    div = det(dx,dy)
    d = [det(*[[case.start.x,case.start.y],[case.end.x,case.end.y]]),det(*[[partition.start.x,partition.start.y],[partition.end.x,partition.end.y]])]
    
    if div < 1e-6: return ".","."

    intersection_x = det(d, dx) / div
    intersection_y = det(d, dy) / div

    split_a = Linedef((case.start.x,case.start.y),(intersection_x,intersection_y))
    split_b = Linedef((intersection_x,intersection_y),(case.end.x,case.end.y))

    return split_a, split_b

def build_bsp(linedefs):
    if not linedefs:
        return
    
    partition = linedefs[0] # TEST CASE - THIS SHOULD BE REPLACED FOR OPTIMAL PERFORMANCE AND SIMPLICITY
    front_division = []
    back_division = []
    on_division = []

    for line in linedefs[1:]:
        div = getdiv_linedef(line,partition)
        if div=="back": back_division.append(line)
        elif div=="front": front_division.append(line)
        elif div=="on": on_division.append(line) # arbitary, could be back if u wanted ACTUALLY NVM
        elif div=="span":
            a,b = splitdiv_linedef(line,partition)
            if (a,b) == (".","."):
                continue
            front_division.append(a)
            back_division.append(b)
    node = BSPNode(partition,
        left=build_bsp(front_division),
        right=build_bsp(back_division),
        segments=on_division + [partition]
                   )
    
    return node

def render_bsp(node,player):

    if not node:
        return
    
    mid = ((node.partition.start.x + node.partition.end.x) / 2, (node.partition.start.y + node.partition.end.y) / 2)
    div = getdiv_linedef(Linedef((player.x,player.y),mid),node.partition)
    if div == "front" or div == "span" or div == "on": # front / span / on
        render_bsp(node.right,player)
        draw_wrapper(node.segments)
        render_bsp(node.left,player)
    elif div == "back": # behind
        render_bsp(node.left,player)
        draw_wrapper(node.segments)
        render_bsp(node.right,player)


tree = TextureTree()

tree.add_texture("brick.jpg")

def draw_wrapper(seg):
    for i in seg:
        cam.draw_wall(plr,i,Color(255,255,255),tree,"brick.jpg")
    
bsp_tree = build_bsp(walls)
del walls
render_bsp(bsp_tree,plr)


PLAYERROTATIONSPEED = 2
while True:
    hpprime.eval("WAIT(0.015)")

    hpprime.fillrect(1,0,0,320,120,0,100255)
    hpprime.fillrect(1,0,120,320,120,0,255100)

    ceiling_clip = [0]*SCREEN_WIDTH
    floor_clip = [SCREEN_HEIGHT]*SCREEN_WIDTH

    render_bsp(bsp_tree,plr)

    if hpprime.eval("ISKEYDOWN(7)"): #hpprime.keyboard() == 128: #2**7
        plr.r -= RAD_CONST*PLAYERROTATIONSPEED
    elif hpprime.eval("ISKEYDOWN(8)"): #hpprime.keyboard() == 256: #2**8
        plr.r += RAD_CONST*PLAYERROTATIONSPEED
    if hpprime.eval("ISKEYDOWN(2)"): #hpprime.keyboard() == 4: #2**2
        plr.x += math.sin(plr.r) * 0.1
        plr.y += math.cos(plr.r) * 0.1
        if 0 == 1:
          plr.x -= math.sin(plr.r) * 0.1
          plr.y -= math.cos(plr.r) * 0.1
    elif hpprime.eval("ISKEYDOWN(12)"): #hpprime.keyboard() == 4096: #2**12
        plr.x -= math.sin(plr.r) * 0.1
        plr.y -= math.cos(plr.r) * 0.1
        if 0 == 1:
           plr.x += math.sin(plr.r) * 0.1
           plr.y += math.cos(plr.r) * 0.1
    #hpprime.line(1,160,120,160-10*math.sin(plr.r*(math.pi/math.pi)),120-10*math.cos(plr.r*(math.pi/math.pi)),255255)
    hpprime.eval("INVERT_P(G1,155,120,165,120)")
    hpprime.eval("INVERT_P(G1,160,115,160,125)")
    hpprime.eval("INVERT_P(G1,160,120,160,120)")
    hpprime.blit(0,0,0,1)


#END

START()
BEGIN
DIMGROB_P(G1,320,240,#000000);
DIMGROB_P(G2,512,512,#000000);
DIMGROB_P(G3,512,512,#000000);
DIMGROB_P(G4,512,512,#000000);
DIMGROB_P(G5,512,512,#000000);
DIMGROB_P(G6,512,512,#000000);
DIMGROB_P(G7,512,512,#000000);
DIMGROB_P(G8,512,512,#000000);
DIMGROB_P(G9,128,128,#000000);
PYTHON(Doom);
END;
