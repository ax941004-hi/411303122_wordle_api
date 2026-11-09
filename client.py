import sys
import os
import pygame
import requests

# 桌面 client 在本機執行，透過這個網址呼叫雲端 FastAPI server。
API_BASE_URL = "https://wordle-server-a076.onrender.com"
#API_BASE_URL = "http://127.0.0.1:8000"


# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_MUTED = (160, 160, 160)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色
COLOR_LINE = (80, 80, 80)
COLOR_HARD_MODE = (235, 175, 45)

pygame.init()
# 任務三：將視窗寬度從 500 擴大為 700
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")

font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
stats_font = pygame.font.SysFont("Arial", 16)
history_font = pygame.font.SysFont("Arial", 22, bold=True)


class WordleGame:
    def __init__(self):
        self.hard_mode = False          # 任務四：預設為 False
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.history_words = []         # 任務三：側邊欄猜過的單字紀錄
        self.stats = {"total": 0, "wins": 0, "win_rate": 0}
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, H for Hard Mode"
        self.start_new_game()

    def start_new_game(self):
        """向 FastAPI 伺服器請求建立新的一局"""
        try:
            # 任務四：傳遞 hard_mode 參數
            res = requests.post(
                f"{API_BASE_URL}/api/new-game",
                json={"hard_mode": self.hard_mode},
                timeout=60
            )
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.history_words = []
                self.row = 0
                self.col = 0
                self.game_over = False
                self.message = "New game started!"
                if "stats" in data:
                    self.stats = data["stats"]
                else:
                    self.sync_stats()
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def sync_stats(self):
        """向 /api/stats 取得目前歷史勝率數據"""
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
            if res.status_code == 200:
                self.stats = res.json()
        except requests.exceptions.RequestException:
            pass

    def submit_guess(self):
        """將當前行單字發送至 FastAPI 驗證"""
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)

            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]

                # 依據後端回傳更新格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                # 任務三：將猜測成功的單字加入歷史面板
                self.history_words.append(guess_word)

                # 更新最新勝率數據
                if "stats" in data:
                    self.stats = data["stats"]

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        # 任務一：6 次機會用盡失敗時揭曉答案
                        target = data.get("target_word", "UNKNOWN")
                        self.message = f"Game Over! The word was {target}. Press R to restart."
                        self.game_over = True
                    else:
                        # 任務一：顯示剩餘次數
                        tries_left = 6 - self.row
                        self.message = f"Keep guessing! ({tries_left} tries left)"

            elif res.status_code == 400:
                detail = res.json().get("detail", "")
                # 任務二：若單字不在字庫中，顯示指定提示
                if "Word not in dictionary" in detail:
                    self.message = "Not in word list!"
                else:
                    self.message = detail
                # 任務二：不消耗猜測次數（self.row 不變，保留輸入以便 Backspace 修改）

            else:
                self.message = res.json().get("detail", "Error processing guess")

        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        # 1. 只有在遊戲結束時，按 R 鍵才會重開局
        if self.game_over:
            if event.key == pygame.K_r:
                self.start_new_game()
            return

        # 2. 任務四：按鍵 H 切換硬核模式開關並開新局
        if event.key == pygame.K_h:
            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        # 3. 刪除字母
        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""

        # 4. 送出猜測
        elif event.key == pygame.K_RETURN:
            self.submit_guess()

        # 5. 一般打字輸入字母（按 R 會正常作為字母輸入，不會觸發遊戲重置）
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)

        # 任務四：畫面右上角顯示目前模式
        mode_str = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_color = COLOR_HARD_MODE if self.hard_mode else COLOR_TEXT_MUTED
        mode_surf = small_font.render(mode_str, True, mode_color)
        surface.blit(mode_surf, (WIDTH - 140, 15))

        # 繪製左側 6x5 遊戲網格
        margin_x, margin_y = 50, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)

                # 背景外框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                # 字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 底部狀態提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(250, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)

        # 任務三：側邊欄分隔線 (x = 490)
        pygame.draw.line(surface, COLOR_LINE, (490, 20), (490, HEIGHT - 20), 2)

        # 任務三：側邊欄上方即時勝率統計
        t = self.stats.get("total", 0)
        w = self.stats.get("wins", 0)
        r = self.stats.get("win_rate", 0)
        stats_line = f"Total: {t} | Wins: {w} | Win Rate: {r}%"
        stats_surf = stats_font.render(stats_line, True, COLOR_TEXT)
        surface.blit(stats_surf, (505, 55))

        # 任務三：側邊欄已猜單字歷史紀錄列表
        title_surf = small_font.render("History Guesses", True, COLOR_TEXT_MUTED)
        surface.blit(title_surf, (510, 95))

        start_y = 130
        for idx, word in enumerate(self.history_words):
            item_surf = history_font.render(f"{idx + 1}.  {word}", True, COLOR_TEXT)
            surface.blit(item_surf, (515, start_y + idx * 36))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
