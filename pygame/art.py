"""Slice generated atlases at runtime, preserving alpha and shared proportions."""
import pygame as pg


def atlas_cells(path, columns, rows):
    sheet = pg.image.load(str(path)).convert_alpha()
    width, height = sheet.get_size()
    # Generation may leave unequal row gutters; locate the actual alpha bands.
    mask = pg.mask.from_surface(sheet,128)
    line = pg.Mask((width,1),fill=True)
    bands = []
    row_counts = []
    for y in range(height):
        count = mask.overlap_area(line,(0,y))
        row_counts.append(count)
        if count>5:
            if not bands or y-bands[-1][1]>12:
                bands.append([y,y])
            else:
                bands[-1][1] = y
    if len(bands)==rows:
        row_edges = [0]+[(bands[i][1]+bands[i+1][0])//2 for i in range(rows-1)]+[height]
    else:
        row_edges = [0]
        margin = max(2,round(height/rows*0.18))
        for i in range(1,rows):
            nominal = round(i*height/rows)
            candidates = range(max(1,nominal-margin),min(height-1,nominal+margin))
            row_edges.append(min(candidates,key=lambda y:(row_counts[y],abs(y-nominal))))
        row_edges.append(height)
    cells = []
    for row in range(rows):
        top,bottom = row_edges[row],row_edges[row+1]
        row_mask = pg.mask.from_surface(sheet.subsurface((0,top,width,bottom-top)),128)
        vertical = pg.Mask((1,bottom-top),fill=True)
        counts = [row_mask.overlap_area(vertical,(x,0)) for x in range(width)]
        column_edges = [0]
        margin = max(2,round(width/columns*0.18))
        for i in range(1,columns):
            nominal = round(i*width/columns)
            candidates = range(max(1,nominal-margin),min(width-1,nominal+margin))
            column_edges.append(min(candidates,key=lambda x:(counts[x],abs(x-nominal))))
        column_edges.append(width)
        for column in range(columns):
            left, right = column_edges[column],column_edges[column+1]
            cell = sheet.subsurface((left,top,right-left,bottom-top)).copy()
            # Discard stray pixels and fragments from a neighboring cell.
            component = pg.mask.from_surface(cell,128).connected_component()
            alpha = component.to_surface(setcolor=(255,255,255,255),unsetcolor=(0,0,0,0))
            cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            bounds = cell.get_bounding_rect(min_alpha=128)
            if not bounds.width or not bounds.height:
                raise ValueError('Empty sprite cell in '+str(path))
            cells.append(cell.subsurface(bounds).copy())
    return cells


def fit_cycle(cells, size, padding=2, anchor='feet'):
    # A shared scale prevents every pose from changing the character's size.
    head_rows = []
    if anchor=='head':
        for cell in cells:
            strip = pg.mask.from_surface(cell.subsurface((0,0,max(1,round(cell.get_width()*0.18)),cell.get_height())),128)
            scanline = pg.Mask((strip.get_size()[0],1),fill=True)
            counts = [strip.overlap_area(scanline,(0,y)) for y in range(cell.get_height())]
            halfway,total = sum(counts)/2,0
            for y,count in enumerate(counts):
                total += count
                if total>=halfway:
                    head_rows.append(y)
                    break
        above = max(head_rows)
        below = max(c.get_height()-y for c,y in zip(cells,head_rows))
        height = above+below
    else:
        height = max(c.get_height() for c in cells)
    scale = min((size[0]-padding*2)/max(c.get_width() for c in cells),
                (size[1]-padding*2)/height)
    frames = []
    for index,cell in enumerate(cells):
        image = pg.transform.scale(cell,(max(1,round(cell.get_width()*scale)),
                                        max(1,round(cell.get_height()*scale))))
        canvas = pg.Surface(size,pg.SRCALPHA)
        rect = image.get_rect(midbottom=(size[0]//2,size[1])) if anchor=='feet' else image.get_rect(center=(size[0]//2,size[1]//2))
        if anchor=='head':
            rect.y = padding+round((above-head_rows[index])*scale)
        canvas.blit(image,rect)
        frames.append(canvas)
    return frames


class WorldArt:
    OBJECT_NAMES = ['journal','journal-open','nest','home-flag',
                    'flowers','ice-cage','lever-down','lever-up',
                    'dive-hole','practice-arch','ocean-rock','seaweed']
    OBJECT_SIZES = [(23,29),(46,34),(65,25),(46,75),
                    (88,36),(48,52),(36,43),(36,43),
                    (72,24),(180,110),(100,65),(38,62)]

    def __init__(self, data):
        babies = atlas_cells(data/'baby-motion-atlas-v2.png',4,2)
        frames = fit_cycle(babies,(32,40),padding=0)
        self.babies = {name:[frames[i] for i in indices] for name,indices in
                       [('walk',range(4)),('idle',[4,5]),('jump',[6]),('fall',[7])]}
        self.baby_right = {name:[pg.transform.flip(f,True,False) for f in cycle]
                           for name,cycle in self.babies.items()}
        cells = atlas_cells(data/'adventure-objects-atlas-v2.png',4,3)
        self.objects = {name:fit_cycle([cell],size,padding=0)[0]
                        for name,size,cell in zip(self.OBJECT_NAMES,self.OBJECT_SIZES,cells)}
        enemies = atlas_cells(data/'enemy-motion-atlas-v2.png',4,4)
        self.enemies = {kind:fit_cycle(enemies[row*4:row*4+4],size,padding=0,anchor='head' if kind=='skua' else 'feet')
                        for row,(kind,size) in enumerate([('crab',(44,30)),('seal',(68,34)),
                                                        ('skua',(48,40)),('spirit',(36,40))])}
        fish = atlas_cells(data/'fish-motion-atlas-v2.png',4,3)
        self.fishes = {kind:fit_cycle(fish[row*4:row*4+4],(36,24),padding=0,anchor='center')
                       for row,kind in enumerate(('orange','blue','gold'))}

    def fish(self, kind, clock):
        return self.fishes[kind][int(clock/0.2)%4]

    def baby(self, state, clock, right=False):
        frames = (self.baby_right if right else self.babies)[state]
        interval = 0.18 if state=='walk' else 0.6
        return frames[int(clock/interval)%len(frames)]

    def place(self, screen, name, feet):
        image = self.objects[name]
        screen.blit(image,image.get_rect(midbottom=(round(feet[0]),round(feet[1]))))
