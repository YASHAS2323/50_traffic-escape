import pygame
import random
import json
import os
import datetime
from game.player import Player,LANE_W
from game.traffic import Car,make_car

LANES=8
WIDTH=LANES*LANE_W
HEIGHT=600
FPS=60
BG=(60,60,60)
MAX_LIVES=3
TOP_N=5
CYCLE_FRAMES=30*FPS   # day <-> night every 30 seconds
NIGHT_ALPHA=170       # how dark the night overlay is (0-255)
BEAM_LEN=240          # headlight reach at night, in pixels
# highscores.json lives in the project root (one level above the game/ folder)
SCORE_FILE=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","highscores.json"))
RIVER_TOP=260      # y where the water band starts
RIVER_H=60         # height of the water band
LOG_SPEED=2        # pixels per frame (positive = moves right)

class Log:
    def __init__(self,x,speed):
        self.rect=pygame.Rect(x,RIVER_TOP,int(LANE_W*1.5),RIVER_H)
        self.speed=speed
    def update(self):
        self.rect.x+=self.speed
        # wrap around so logs keep coming
        if self.speed>0 and self.rect.left>WIDTH: self.rect.right=0
        elif self.speed<0 and self.rect.right<0: self.rect.left=WIDTH
    def draw(self,screen):
        body=self.rect.inflate(0,-12)
        pygame.draw.rect(screen,(120,80,40),body,border_radius=8)
        pygame.draw.rect(screen,(80,50,25),body,3,border_radius=8)
        for x in range(body.left+14,body.right-8,18):
            pygame.draw.line(screen,(95,62,30),(x,body.top+6),(x,body.bottom-6),2)

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen=pygame.display.set_mode((WIDTH,HEIGHT))
        pygame.display.set_caption("Traffic Escape")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("monospace",24,bold=True)
        self.big_font=pygame.font.SysFont("monospace",44,bold=True)
        self.small_font=pygame.font.SysFont("monospace",20,bold=True)
        self.reset()

    def reset(self):
        # full restart: fresh lives, score and difficulty
        self.lives=MAX_LIVES
        self.player=Player(WIDTH//2,HEIGHT-80)
        self.cars=[]
        self.logs=[Log(i*WIDTH//3,LOG_SPEED) for i in range(3)]
        self.timer=0
        self.spawn_interval=50
        self.speed=3
        self.score=0
        self.game_over=False
        self.won=False
        self.night=False            # day/night cycle: starts as day
        self.darkness=0.0           # 0 = full day, 1 = full night (fades smoothly)
        self.cycle_timer=0
        self.car_dir={}             # id(car) -> +1 moving down, -1 moving up
        self.score_saved=False      # make sure each round is recorded only once
        self.last_entry=None
        self.high_scores=self.load_scores()

    # ---------- high score table ----------
    def load_scores(self):
        try:
            with open(SCORE_FILE,"r") as f: data=json.load(f)
        except (OSError,ValueError):
            return []                # missing or corrupted file -> empty table
        if not isinstance(data,list): return []
        good=[e for e in data if isinstance(e,dict) and isinstance(e.get("score"),int)]
        good.sort(key=lambda e:e["score"],reverse=True)
        return good[:TOP_N]

    def save_scores(self,scores):
        try:
            with open(SCORE_FILE,"w") as f: json.dump(scores,f,indent=2)
        except OSError:
            pass                     # never crash the game over a failed save

    def record_score(self):
        self.score_saved=True
        entry={"score":self.score//10,
               "date":datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
        scores=self.load_scores()    # re-read so scores from other sessions are kept
        scores.append(entry)
        scores.sort(key=lambda e:e["score"],reverse=True)
        scores=scores[:TOP_N]
        self.save_scores(scores)
        self.high_scores=scores
        self.last_entry=entry

    def respawn(self):
        # automatic restart after a crash: keeps lives/score/speed, resets positions
        self.player=Player(WIDTH//2,HEIGHT-80)
        self.cars=[]
        self.timer=0

    def lose_life(self):
        self.lives-=1
        if self.lives<=0:
            self.game_over=True   # last life gone: game stops
        else:
            self.respawn()        # otherwise auto restart

    def in_river(self):
        return RIVER_TOP<=self.player.rect.centery<RIVER_TOP+RIVER_H

    def log_under_player(self):
        for l in self.logs:
            if l.rect.collidepoint(self.player.rect.center): return l
        return None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type==pygame.QUIT: return False
            if event.type==pygame.KEYDOWN and event.key==pygame.K_r: self.reset()
        return True

    def update(self):
        if self.game_over or self.won: return
        # day/night cycle
        self.cycle_timer+=1
        if self.cycle_timer>=CYCLE_FRAMES:
            self.cycle_timer=0
            self.night=not self.night
        target=1.0 if self.night else 0.0
        if self.darkness<target: self.darkness=min(target,self.darkness+1.0/FPS)
        elif self.darkness>target: self.darkness=max(target,self.darkness-1.0/FPS)
        keys=pygame.key.get_pressed()
        self.player.move(keys,0,WIDTH)
        self.timer+=1
        if self.timer>=self.spawn_interval:
            lane=random.randint(0,LANES-1)
            self.cars.append(make_car(lane,HEIGHT,self.speed))
            self.timer=0
            self.spawn_interval=max(22,self.spawn_interval-0.2)
        for l in self.logs: l.update()
        died=False
        if self.in_river():
            log=self.log_under_player()
            if log:
                self.player.rect.x+=log.speed          # ride the log
                if not 0<=self.player.rect.centerx<=WIDTH: died=True  # carried off screen
            else:
                died=True                              # fell in the water
            if died: self.lose_life()
        for c in self.cars:
            y0=c.rect.y
            c.update()
            dy=c.rect.y-y0
            if dy: self.car_dir[id(c)]=1 if dy>0 else -1   # remember travel direction
            # cars pass under the river, so no collisions while on it
            if not died and not self.in_river() and c.rect.colliderect(self.player.rect):
                self.lose_life()
                died=True                              # one life per crash
        self.cars=[c for c in self.cars if not c.off_screen(HEIGHT)]
        self.car_dir={id(c):self.car_dir.get(id(c),1) for c in self.cars}
        self.score+=1
        if self.score%300==0: self.speed=min(10,self.speed+0.5)
        if self.player.rect.top<=10:
            self.won=True
        if (self.game_over or self.won) and not self.score_saved:
            self.record_score()

    def draw(self):
        self.screen.fill(BG)
        # road markings
        for i in range(LANES+1):
            pygame.draw.line(self.screen,(100,100,100),(i*LANE_W,0),(i*LANE_W,HEIGHT),2)
        for y in range(0,HEIGHT,60):
            for i in range(LANES):
                pygame.draw.rect(self.screen,(200,200,100),pygame.Rect(i*LANE_W+LANE_W//2-3,y,6,30))
        # sidewalks
        pygame.draw.rect(self.screen,(150,130,110),pygame.Rect(0,HEIGHT-50,WIDTH,50))
        pygame.draw.rect(self.screen,(150,130,110),pygame.Rect(0,0,WIDTH,30))
        for c in self.cars: c.draw(self.screen)
        # river drawn over the cars, then the logs on top of it
        river=pygame.Rect(0,RIVER_TOP,WIDTH,RIVER_H)
        pygame.draw.rect(self.screen,(40,100,190),river)
        for x in range(0,WIDTH,40):
            pygame.draw.line(self.screen,(90,150,220),(x,RIVER_TOP+15),(x+20,RIVER_TOP+15),2)
            pygame.draw.line(self.screen,(90,150,220),(x+20,RIVER_TOP+45),(x+40,RIVER_TOP+45),2)
        for l in self.logs: l.draw(self.screen)
        self._draw_night()
        for c in self.cars: self._draw_lamps(c)
        self.player.draw(self.screen)
        hud=pygame.Rect(0,0,WIDTH,30)
        pygame.draw.rect(self.screen,(20,20,20),hud)
        s=self.font.render(f"Score: {self.score//10}  Lives: {max(self.lives,0)}  R=Restart",True,(220,220,220))
        self.screen.blit(s,(6,4))
        if self.night:   # moon
            pygame.draw.circle(self.screen,(225,225,245),(WIDTH-20,15),8)
            pygame.draw.circle(self.screen,(20,20,20),(WIDTH-16,12),7)
        else:            # sun
            pygame.draw.circle(self.screen,(255,210,60),(WIDTH-20,15),8)
        if self.game_over:
            self._msg("GAME OVER",(220,60,60))
        if self.won:
            self._msg("YOU MADE IT!",(80,220,80))
        pygame.display.flip()

    # ---------- day / night ----------
    def _under_river(self,c):
        return RIVER_TOP<=c.rect.centery<RIVER_TOP+RIVER_H   # cars are hidden here

    def _front(self,c):
        d=self.car_dir.get(id(c),1)
        return d,(c.rect.bottom if d>0 else c.rect.top)

    def _draw_night(self):
        if self.darkness<=0: return
        d=self.darkness
        dark=(5,8,30)
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill(dark+(int(NIGHT_ALPHA*d),))
        for c in self.cars:
            if self._under_river(c): continue
            dr,front=self._front(c)
            w=c.rect.width
            x1=c.rect.left+w*0.15
            x2=c.rect.right-w*0.15
            # nested cones, biggest/faintest first; each one "cuts" the darkness
            for length,spread,left in ((1.0,0.6,0.75),(0.7,0.4,0.5),(0.4,0.25,0.25)):
                far=front+dr*BEAM_LEN*length*d
                sp=w*spread
                pts=[(x1,front),(x2,front),(x2+sp,far),(x1-sp,far)]
                pygame.draw.polygon(ov,dark+(int(NIGHT_ALPHA*d*left),),pts)
        self.screen.blit(ov,(0,0))

    def _draw_lamps(self,c):
        if self._under_river(c): return
        dr,front=self._front(c)
        w=c.rect.width
        r=3+int(2*self.darkness)          # lamps glow a bit bigger at night
        y=front-dr*3
        for x in (c.rect.left+w*0.22,c.rect.right-w*0.22):
            pygame.draw.circle(self.screen,(255,240,150),(int(x),int(y)),r)

    def _msg(self,text,color):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,170))
        self.screen.blit(ov,(0,0))
        def center(surf,y): self.screen.blit(surf,(WIDTH//2-surf.get_width()//2,y))
        center(self.big_font.render(text,True,color),80)
        center(self.font.render(f"Your score: {self.score//10}",True,(220,220,220)),140)
        center(self.font.render("TOP 5",True,(255,200,60)),190)
        for i in range(TOP_N):
            if i<len(self.high_scores):
                e=self.high_scores[i]
                row=f"{i+1}. {e['score']:>5}  {e.get('date','')[:10]}"
                col=(255,230,90) if e is self.last_entry else (190,190,190)
            else:
                row=f"{i+1}. -----"
                col=(110,110,110)
            center(self.small_font.render(row,True,col),228+i*28)
        center(self.font.render("Press R to Restart",True,(200,200,200)),228+TOP_N*28+20)

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()