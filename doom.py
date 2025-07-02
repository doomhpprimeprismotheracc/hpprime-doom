#PYTHON Doom
import hpprime
import math

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
EPSILON = 1e-6
RAD_CONST = math.pi / 180


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
        return hpprime.eval("G{0} = AFiles({1})".format(str(surface),self.fileno))

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
        return int(v*h) % h
    
    def find_texpix(self,sx,sy,x0,x1,y0up,y0down,y1up,y1down,w=128,h=128):
        return self.find_texcolumn(sx,x0,x1,w), self.find_texrow(sx,sy,x0,x1,y0up,y0down,y1up,y1down,h)
    

    def get_texture_pixel(self,fileno,x,y):
        if self.loaded != self.fileno:
            self.load_texture(fileno)
            col = hpprime.eval("GETPIX(G9,{0},{1})".format(str(x),str(y)))
            rr = col[0:1]
            gg = col[2:3]
            bb = col[4:5]
            return Color(int(rr,16),int(bb,16),int(gg,16))



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
            return -10,0,0,0,0,0
        
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
            return x0,x1,r0,r1,r2,r3
            

        else:
            r0,r1,r2,r3 = inner()
            return x0,x1,r0,r1,r2,r3

    def draw_quad(self,x0,y0,x1,y1,x2,y2,x3,y3,color:Color):
        """Draws a quadrilateral. Included so that this code is more easily adaptable to other platforms."""
        hpprime.eval( "FILLPOLY_P(G1,{0}({1},{2}),({3},{4}),({5},{6}),({7},{8}){9},RGB({10},{11},{12}))".format("{",x0,y0,x1,y1,x2,y2,x3,y3,"}",color.R,color.G,color.B))
    
    def draw_pix(self,x0,y0,Color:Color):
        """Sets a pixel at x0,y0 to color Color. Included so that this code is more easily adaptable to other platforms. TBH this shouldn't even be that hard to implement anyways, but you're welcome."""
        hpprime.eval( "PIXON(G1,{0},{1},RGB({2},{3},{4}))".format(str(x0),str(y0),str(Color.R),str(Color.G),str(Color.B)))
    
    def draw_wall(self,player,wall,Color):
        """Draws a wall in color Color. ON THE SCREEN. NO WAY!!!!"""
        x0,x1,r0,r1,r2,r3 = self.project_wall(player,wall)
        if (x0,x1,r0,r1,r2,r3) == (-10,0,0,0,0,0):
            return -1
        self.draw_quad(x0,r0,x0,r1,x1,r3,x1,r2,Color)

    def draw_textured_quad(self,ttree:TextureTree,fileno,x0,x1,r0,r1,r2,r3):
        xc = 0
        yc = 0
        for i in range(x0,x1):
            yc = 0
            xc+=1
            px = ttree.find_texcolumn(x0+xc,x0,x1)
            t = (px-x0) / (x1-x0)
            y0 = r0 + t * (r2 - r0)
            y1 = r1 + t * (r3 - r1)
            for j in range(y0,y1):
                yc+=1
                py = ttree.find_texrow(px,y0+yc,x0,x1,r0,r1,r2,r3)
                


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
    Wall((5,5),(5,-5)),
    Wall((5,-5),(-5,-5)),
    Wall((-5,-5),(-5,5)),
    Wall((-5,5),(5,5))
]

plr = Player(0,0,0)
cam = Camera()

def getdiv_linedef(case,partition):
    start = getdiv_point(case.start,partition.start,partition.dx,partition.dy) 
    end = getdiv_point(case.end,partition.end,partition.dx,partition.dy) 
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
    div = ((case.x - partition.x) * dy) - ((case.y - partition.y) * dx)
    return div

def splitdiv_linedef(case,partition):

    dx = [case.start.x - case.end.x, partition.start.x - partition.end.x]
    dy = [case.start.y - case.end.y, partition.start.y - partition.end.y]
    def det(a,b):
        return a[0] * b[1] - a[1] * b[0]
    div = det(dx,dy)
    d = [det(*[[case.start.x,case.start.y],[case.end.x,case.end.y]]),det(*[[partition.start.x,partition.start.y],[partition.end.x,partition.end.y]])]

    if div < 1e-6:
        return ".","."

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

def draw_wrapper(seg):
    for i in seg:
        cam.draw_wall(plr,i,Color(255,255,255))
    
bsp_tree = build_bsp(walls)
render_bsp(bsp_tree,plr)

tree = TextureTree()

tree.add_texture("brick.png")

PLAYERROTATIONSPEED = 2
while True:
    hpprime.eval("WAIT(0.015)")

    hpprime.fillrect(1,0,0,320,120,0,100255)
    hpprime.fillrect(1,0,120,320,120,0,255100)

    render_bsp(bsp_tree,plr)
    #print(plr.x,plr.y,plr.r)

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
DIMGROB_P(G9,512,512,#000000);
PYTHON(Doom);
END;
