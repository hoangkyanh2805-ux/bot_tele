"""Tu dong dang nhap VNC va cai bot. Bam vao cua so VNC trong 10 giay."""
import time
import pyautogui
import pyperclip

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

INSTALL_CMD = "curl -fsSL https://files.catbox.moe/kw8vao.sh | bash"
PASSWORD = "x8Bz4MZGvz"

print("=== TU DONG CAI BOT TREN VNC ===")
print("MO VNC CONSOLE, BAM VAO MAN HINH DEN, GIU CHUOT O DO!")
for i in range(15, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

# Click giua man hinh de focus VNC
w, h = pyautogui.size()
pyautogui.click(w // 2, h // 2)
time.sleep(0.5)
pyautogui.write("root", interval=0.08)
pyautogui.press("enter")
time.sleep(1.5)
pyautogui.write(PASSWORD, interval=0.05)
pyautogui.press("enter")
time.sleep(4)
pyperclip.copy(INSTALL_CMD)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)
pyautogui.press("enter")
print("Da gui lenh cai dat. Xem VNC doi 1-2 phut...")
