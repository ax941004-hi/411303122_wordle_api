import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 任務三：全域勝率統計 (Total Games 與 Wins)
stats_db = {
    "total_games": 0,
    "wins": 0
}

games_db: Dict[str, dict] = {}


class NewGameRequest(BaseModel):
    hard_mode: Optional[bool] = False  # 任務四：可選參數


class GuessRequest(BaseModel):
    game_id: str
    guess: str


def get_stats_data() -> dict:
    """計算並回傳勝率統計資料"""
    total = stats_db["total_games"]
    wins = stats_db["wins"]
    win_rate = round((wins / total) * 100) if total > 0 else 0
    return {
        "total": total,
        "wins": wins,
        "win_rate": win_rate
    }


# 任務三：新增 /api/stats 路由
@app.get("/api/stats")
def get_stats():
    return get_stats_data()


@app.post("/api/new-game")
def start_new_game(req: Optional[NewGameRequest] = None):
    """建立新遊戲，支援 hard_mode 參數"""
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    hard_mode = req.hard_mode if req else False

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": hard_mode,
        "confirmed_greens": {},  # 記錄已鎖定的綠色字母 {位置索引: 字母}
        "is_counted": False
    }

    return {
        "game_id": game_id,
        "message": "New game started!",
        "stats": get_stats_data()
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    game_id = req.game_id
    guess = req.guess.upper().strip()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game = games_db[game_id]

    if game["status"] != "PLAYING":
        raise HTTPException(status_code=400, detail="Game is already finished.")

    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：單字合法性檢查
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    # 任務四：硬核模式驗證（綠色位置必須維持相同字母）
    if game["hard_mode"]:
        for pos, char in game["confirmed_greens"].items():
            if guess[pos] != char:
                raise HTTPException(
                    status_code=400,
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    target = game["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 第一輪：確認綠色 (correct)
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            if game["hard_mode"]:
                game["confirmed_greens"][i] = guess[i]

    # 第二輪：確認黃色 (present)
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    game["attempts"] += 1
    is_correct = (guess == target)
    target_word_to_return = None

    if is_correct:
        game["status"] = "WON"
        if not game["is_counted"]:
            stats_db["total_games"] += 1
            stats_db["wins"] += 1
            game["is_counted"] = True
    elif game["attempts"] >= 6:
        # 任務一：猜滿 6 次且失敗時揭曉答案
        game["status"] = "LOST"
        target_word_to_return = target
        if not game["is_counted"]:
            stats_db["total_games"] += 1
            game["is_counted"] = True

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target_word_to_return,  # 任務一
        "stats": get_stats_data()              # 任務三
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
