# Hướng dẫn sử dụng Bot Relay Telegram

Bot này lấy bài từ **kênh nguồn** rồi **đăng lại** sang **kênh đích** dưới danh nghĩa bot (không hiện nhãn *Forwarded from*).

---

## Bước 1: Thêm bot vào kênh

1. Tạo bot qua `@BotFather` và lấy token (nếu chưa có).
2. Trong `@BotFather`, chạy `/setprivacy` → chọn **Disable** cho bot.
3. **Thêm bot vào 2 kênh** (hoặc nhiều hơn nếu cần):
   - Kênh **lấy bài** (nguồn)
   - Kênh **gửi bài** (đích)
4. Ở kênh đích, đặt bot làm **admin** và bật quyền **đăng bài**.

---

## Bước 2: Lấy ID kênh

Vào từng kênh, gửi lệnh:

```text
/chat_id
```

Bot trả về ID dạng `-100...`. Ghi lại ID của kênh nguồn và kênh đích.

> Có thể dùng `@username` cho kênh công khai, nhưng ID số ổn định hơn.

---

## Bước 3: Cấp phép kênh nhận bài — `/allow`

Trước khi map, phải **cho phép** các kênh đích nhận tin:

```text
/allow -1002222222222
```

Nhiều kênh cùng lúc:

```text
/allow -1002222222222 -1003333333333
```

Trong đó `-1002222222222` là ID **kênh gửi bài** (đích).

---

## Bước 4: Tạo mapping — `/map`

Map kênh lấy bài → kênh gửi bài:

```text
/map <kênh_lấy_bài> <kênh_gửi_bài>
```

**Ví dụ:**

```text
/map -1001111111111 -1002222222222
```

- `-1001111111111` = kênh **lấy bài** (nguồn)
- `-1002222222222` = kênh **gửi bài** (đích)

Một kênh nguồn có thể gửi sang nhiều kênh đích:

```text
/allow -1002222222222 -1003333333333
/map -1001111111111 -1002222222222
/map -1001111111111 -1003333333333
```

---

## Các lệnh khác

| Lệnh | Mô tả |
|------|--------|
| `/chat_id` | Xem ID kênh/group hiện tại |
| `/allow <đích...>` | Thêm kênh được phép nhận bài |
| `/map <nguồn> <đích>` | Tạo tuyến lấy bài → gửi bài |
| `/map_list` | Xem toàn bộ mapping đang có |
| `/remove <nguồn> [đích]` | Xóa mapping (bỏ đích = xóa hết tuyến của nguồn đó) |

**Ví dụ xóa một tuyến:**

```text
/remove -1001111111111 -1002222222222
```

---

## Lưu ý

- Chỉ **admin** (khai báo trong `ADMIN_IDS` file `.env`) mới dùng được `/allow`, `/map`, `/remove`, `/map_list`.
- Sau khi map xong, mọi bài mới ở kênh nguồn sẽ tự động được đăng sang kênh đích.
- Bot bỏ qua tin do bot khác gửi để tránh lặp vô hạn.
- Tin đã sửa hoặc xóa ở kênh nguồn **không** tự đồng bộ sang kênh đích.

---

## Quy trình nhanh (tóm tắt)

```text
1. Thêm bot vào kênh lấy bài + kênh gửi bài
2. /chat_id          → lấy ID từng kênh
3. /allow <đích>     → cho phép kênh nhận bài
4. /map <nguồn> <đích> → bật tuyến lấy bài → gửi bài
```
