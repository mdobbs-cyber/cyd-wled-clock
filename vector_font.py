# Vector Font (Simplex-like)
# Digits defined as list of line segments (x1,y1, x2,y2) nominal 0-10 range

class VectorFont:
    def __init__(self, display, width=20, height=30):
        self.d = display
        self.w = width
        self.h = height
        
        # Grid 10x10 nominal
        # 0
        self.d0 = [
            (2,0, 8,0), (8,0, 10,2), (10,2, 10,8), (10,8, 8,10), 
            (8,10, 2,10), (2,10, 0,8), (0,8, 0,2), (0,2, 2,0), (2,8, 8,2) # Slash
        ]
        
        # 1 
        self.d1 = [
            (2,2, 5,0), (5,0, 5,10), (2,10, 8,10)
        ]
        
        # 2
        self.d2 = [
            (0,2, 2,0), (2,0, 8,0), (8,0, 10,2), (10,2, 10,4),
            (10,4, 0,10), (0,10, 10,10)
        ]
        
        # 3
        self.d3 = [
            (0,0, 10,0), (10,0, 5,5), (5,5, 10,5), (10,5, 10,8),
            (10,8, 8,10), (8,10, 2,10), (2,10, 0,8)
        ]
        
        # 4
        self.d4 = [
            (7,10, 7,0), (7,0, 0,7), (0,7, 10,7)
        ]
        
        # 5
        self.d5 = [
            (10,0, 0,0), (0,0, 0,4), (0,4, 8,4), (8,4, 10,6),
            (10,6, 10,8), (10,8, 8,10), (8,10, 0,10)
        ]
        
        # 6
        self.d6 = [
            (10,2, 8,0), (8,0, 2,0), (2,0, 0,2), (0,2, 0,8),
            (0,8, 2,10), (2,10, 8,10), (8,10, 10,8), (10,8, 10,5), (10,5, 0,5)
        ]
        
        # 7
        self.d7 = [
            (0,0, 10,0), (10,0, 0,10)
        ]
        
        # 8
        self.d8 = [
            (2,0, 8,0), (8,0, 10,2), (10,2, 10,4), (10,4, 8,5),
            (8,5, 2,5), (2,5, 0,4), (0,4, 0,2), (0,2, 2,0),
            (2,5, 8,5), (8,5, 10,6), (10,6, 10,8), (10,8, 8,10),
            (8,10, 2,10), (2,10, 0,8), (0,8, 0,6), (0,6, 2,5)
        ]
        
        # 9
        self.d9 = [
            (10,5, 0,5), (0,5, 0,2), (0,2, 2,0), (2,0, 8,0), 
            (8,0, 10,2), (10,2, 10,8), (10,8, 8,10), (8,10, 2,10)
        ]
        
        self.digits = [self.d0, self.d1, self.d2, self.d3, self.d4, self.d5, self.d6, self.d7, self.d8, self.d9]

    def draw_digit(self, num, x, y, color):
        lines = self.digits[num]
        
        # Scale factors
        sx = self.w / 10.0
        sy = self.h / 10.0
        
        for l in lines:
            x0 = x + int(l[0] * sx)
            y0 = y + int(l[1] * sy)
            x1 = x + int(l[2] * sx)
            y1 = y + int(l[3] * sy)
            self.d.line(x0, y0, x1, y1, color)
            # Draw adjacent line for thickness?
            # self.d.line(x0+1, y0, x1+1, y1, color)
