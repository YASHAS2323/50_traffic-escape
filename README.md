## STUDENT DETAILS
NAME: YASHAS C
SRN: PES1UG24CS544
SECTION: I

# Traffic Escape

Cross 8 lanes of oncoming traffic to reach the other side (Frogger-style).

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| A/D or Left/Right | Change lane |
| W / UP | Move forward |
| S / DOWN | Move back |
| R | Restart |

## Tasks to Complete

### Task 1: Lives System
> Give the player 3 lives. Getting hit loses one; game over at 0.



### Task 2: Moving Log/Raft Lane
> Add a safe lane where the player must hop on a moving log to cross.



### Task 3: High Score Table
> Track and display the top 5 scores across sessions (save to JSON).


### Task 4: Day/Night Cycle
> Every 30 seconds switch between day and night. At night, cars have headlights visible further ahead.


## Folder Structure

```
traffic-escape/
├── main.py
├── requirements.txt
├── game/
│   ├── __init__.py
│   ├── game_engine.py
│   ├── player.py
│   └── traffic.py
└── README.md
```

## Submission Checklist

Submission is only the following three things:

- [] A 10-second video of gameplay **before** your changes, showing the bug/broken behavior
- [] A 10-second video of gameplay **after** your changes, showing the bug fixed and the new features working
- [] The Chat/LLM used page link, with the complete chat history

