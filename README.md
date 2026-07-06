# Telegram Group Relay Bot

Bot nhận tin nhắn từ group nguồn rồi **đăng lại dưới danh nghĩa bot** vào một hoặc
nhiều group đích. Tin ở group đích không có nhãn `Forwarded from`.

Hỗ trợ text, định dạng, ảnh, video, file, sticker, voice, poll và album. Service
message, invoice, giveaway và một số nội dung bị Telegram bảo vệ không thể copy.

## 1. Tạo và cấp quyền cho bot

1. Nhắn `@BotFather`, chạy `/newbot`, rồi lấy token.
2. Trong `@BotFather`, chạy `/setprivacy` và chọn **Disable** cho bot. Sau khi đổi,
   nên xóa bot khỏi group nguồn rồi thêm lại.
3. Thêm bot vào tất cả group nguồn và group đích.
4. Nên đặt bot làm admin ở group nguồn để bot luôn nhận đủ tin nhắn. Ở group đích,
   bot phải có quyền gửi tin và gửi media.

Nếu group bật **Restrict Saving Content / Protect Content**, Telegram có thể từ
chối việc copy nội dung ra ngoài.

## 2. Cài đặt

Yêu cầu Python 3.10 trở lên.

```powershell
cd C:\Users\20119\Desktop\Bot_Tele
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item mappings.example.json mappings.json
```

Mở `.env` và thay `TELEGRAM_BOT_TOKEN`. Không gửi token cho người khác và không
commit file `.env` lên Git.

## 3. Lấy ID group

Thêm bot vào group, gửi:

```text
/chat_id
```

Bot trả về ID dạng `-100...`. Làm lần lượt cho các group nguồn và đích.

## 4. Cấu hình bằng lệnh Telegram

Đặt Telegram **user ID** của người được phép quản trị vào `ADMIN_IDS` trong
`.env`. Nhiều người quản trị được ngăn cách bằng dấu phẩy:

```env
ADMIN_IDS=123456789,987654321
```

Quy trình tạo mapping gồm hai bước:

```text
/allow -1002222222222 -1003333333333
/map -1001111111111 -1002222222222
/map -1001111111111 -1003333333333
```

Lệnh đầu cấp phép hai channel được nhận tin. Hai lệnh sau tạo mapping 1-2 từ
nguồn `-1001111111111`. Bot kiểm tra mình đã có mặt trong cả nguồn lẫn đích; với
channel đích, bot phải là admin và có quyền đăng bài.

Có thể dùng ID `-100...` hoặc `@username` cho channel công khai. ID số được khuyến
nghị vì không đổi khi channel đổi username.

Bot chỉ có năm lệnh:

- `/allow <channel...>`: thêm các channel được phép nhận tin.
- `/map <nguồn> <đích>`: tạo một mapping nguồn-đích.
- `/map_list`: xem toàn bộ mapping hiện tại.
- `/remove <nguồn> [đích]`: xóa một mapping; bỏ đích để xóa toàn bộ nguồn.
- `/chat_id`: xem ID channel/group hiện tại.

Ví dụ xóa một tuyến:

```text
/remove -1001111111111 -1002222222222
```

Mọi thay đổi bằng lệnh được lưu ngay vào `mappings.json` và vẫn còn sau khi bot
khởi động lại. Bot vẫn tương thích với định dạng JSON cũ và sẽ chuyển sang cấu
trúc mới sau lần thay đổi đầu tiên.

## 5. Chạy bot

```powershell
python bot.py
```

Giữ cửa sổ PowerShell đang chạy. Dừng bằng `Ctrl+C`.

## Lưu ý vận hành

- Bot dùng `copyMessage/copyMessages`, không dùng `forwardMessage`.
- Tin cũ trong lúc bot tắt sẽ được xử lý khi bot chạy lại nếu
  `DROP_PENDING_UPDATES=false`.
- Bot bỏ qua tin do bot khác gửi để tránh vòng lặp mapping.
- Tin đã sửa hoặc đã xóa ở group nguồn hiện không đồng bộ sang group đích.
- Nếu một đích lỗi quyền hoặc sai ID, các đích còn lại vẫn tiếp tục nhận tin;
  xem chi tiết lỗi trong cửa sổ chạy bot.
